# Ontology Init Interview Script

Detailed conversation flow for `/wiki-ontology-init`. The agent should follow these stages in order, but may shorten or skip stages when the user's answers make later questions unnecessary.

## Global rules

- **Load the template first.** Read `references/ontology-template.yaml` and use its structure as the skeleton. Every question maps to a section of the output YAML.
- **Default-heavy, user-lean.** Always propose a default and ask "OK? / change? / skip?" instead of open-ended questions when possible.
- **Progressive disclosure.** Complete one stage, show a mini-summary, then ask "Continue to next stage?" — the user can stop and resume later.
- **Idempotent.** If `wiki/ontology.yaml` already exists, read it first and treat the interview as an edit session. Offer the user "Which stage do you want to revisit?" instead of starting from scratch.
- **Example-driven.** When asking about a class or relation, show 1–2 concrete examples tailored to the user's project type (from Stage 0).
- **Write incrementally.** Save progress to `wiki/ontology.yaml` after each stage, so an interrupted session can resume.

---

## Running Example

All **"Dialogue example"** blocks below follow the same scenario for coherence:

- **Project:** QuickNotes — a small SaaS team building a note-taking app
- **Users:** 5-person team (PM, 2 engineers, 1 designer, 1 QA)
- **Timeline:** 2026-04 → 2026-10 (MVP to public launch)

When the user's project differs, adapt the examples but keep the same shape (propose → confirm → record).

Legend for dialogue blocks:

> 💬 **Agent** — the question or proposal
> ✍️ **User** — a plausible answer
> ⚙️ **Action** — what the agent records to `ontology.yaml` (and optionally commits to disk)

---

## Stage 0 — Project Profiling

**Purpose:** Identify project type so later stages can tailor questions and defaults.

**Questions:**

1. "이 위키를 어떤 프로젝트의 지식베이스로 사용하시나요?
   - (a) software-project — 소프트웨어 개발
   - (b) research — 연구/논문 작성
   - (c) product — 제품 기획·운영
   - (d) campaign — 마케팅/캠페인
   - (e) operations — 조직 운영/상시 업무
   - (f) personal — 개인 학습/독서 노트
   - (g) other — 자유 기술"

2. "프로젝트 이름과 한 문장 설명을 알려주세요."

3. "기간이 정해져 있나요? (start_date, end_date — ongoing이면 각각 null)"

**Output (partial ontology.yaml):**

```yaml
version: 1
project:
  name: "..."
  type: "..."
  description: "..."
  start_date: ...
  end_date: ...
```

**Type-based defaults the agent should apply in later stages:**

| type             | Actor focus | Activity focus | Artifact focus | Objective focus | Resource | Context |
|------------------|-------------|----------------|----------------|-----------------|----------|---------|
| software-project | Team, Role  | Task, Phase    | CodeArtifact, Deliverable | Requirement, Milestone | off | on (Technology) |
| research         | Person      | Experiment*, Phase | Report, Design | Goal, KPI      | off      | on (Domain)     |
| product          | Team, Stakeholder | Task, Decision | Document, Deliverable | Goal, KPI    | on       | off             |
| campaign         | Team, Stakeholder | Event, Task   | Report, Design  | KPI             | on       | off             |
| operations       | Role, Team  | Meeting, Decision | Report      | KPI, Risk       | on       | off             |
| personal         | Person      | —              | Document        | Goal            | off      | off             |
| other            | all off; ask individually                                                            |

*Add `Experiment` as a custom Activity class when type=research.

Offer these defaults explicitly: "For a `<type>` project, I suggest activating: <axes>. Keep these defaults or customize?"

### Dialogue example

> 💬 **Agent:** 이 위키를 어떤 프로젝트의 지식베이스로 사용하시나요? (a) software-project / (b) research / (c) product / (d) campaign / (e) operations / (f) personal / (g) other
>
> ✍️ **User:** a. 사실은 제품이기도 한데 코드 중심이라 software-project 쪽이 맞아요.
>
> 💬 **Agent:** 이해했습니다. software-project로 진행하겠습니다. 프로젝트 이름과 한 문장 설명은요?
>
> ✍️ **User:** QuickNotes — 팀원 5명이 만드는 SaaS 메모 앱입니다.
>
> 💬 **Agent:** 기간은요? (시작·종료일, ongoing이면 각각 null)
>
> ✍️ **User:** 2026-04-01 시작, 10월 말 퍼블릭 런칭 예정.
>
> ⚙️ **Action:** write partial `ontology.yaml`:
>
> ```yaml
> version: 1
> project:
>   name: "QuickNotes"
>   type: "software-project"
>   description: "5-person team building a SaaS note-taking app"
>   start_date: 2026-04-01
>   end_date: 2026-10-31
> ```
>
> 💬 **Agent:** software-project에 대한 기본 구성은 **Actor: Team·Role** / **Activity: Task·Phase** / **Artifact: CodeArtifact·Deliverable** / **Objective: Requirement·Milestone** / **Context: Technology** 입니다. Resource(Budget/Tool)는 기본 off입니다. 이대로 진행할까요, 아니면 수정하시겠어요?
>
> ✍️ **User:** 예산은 추적 안 해도 되는데 Tool(쓰는 서비스들)은 기록하고 싶어요.
>
> ⚙️ **Action:** Mark `Resource.active = true` with only `Tool` class enabled in Stage 5; continue.

---

## Stage 1 — Actor Axis (WHO)

**Purpose:** Define the subjects that own, act, and decide.

**Questions:**

1. "이 프로젝트에 참여하는 주체 중 위키에서 추적하고 싶은 것을 골라주세요.
   기본 제공: Person, Team, Role, Organization, Stakeholder.
   - 사용할 클래스에 ✓
   - 빼고 싶은 것 표시
   - 추가할 커스텀 클래스가 있나요? (예: Vendor, Customer, Reviewer)"

2. For each activated class, ask: "이 클래스에 어떤 속성이 필요한가요? 기본값은 `<default properties>` 입니다. 유지/추가/삭제?"

3. (Seed instances — optional) "현재 알고 있는 팀이나 핵심 인물을 2~3명 예시로 알려주시겠어요? 이름, 역할, 소속 정도면 됩니다. 나중에 채워 넣어도 괜찮습니다."
   - If answered: create seed pages in `wiki/entities/` with `class:` frontmatter.
   - If skipped: move on.

**Output:** populated `axes.Actor.default_classes` in ontology.yaml, optionally seed entity files.

### Dialogue example

> 💬 **Agent:** 이 프로젝트에서 추적할 주체를 고르세요. 기본: **Person, Team, Role** (Organization, Stakeholder는 5인 팀에는 과할 수 있어 일단 빼두었습니다). 어떤가요?
>
> ✍️ **User:** Person은 필요 없을 것 같아요 — 5명이라 Role이면 충분해요. Team도 하나뿐이라 빼죠.
>
> 💬 **Agent:** 그럼 **Role** 하나만 남기겠습니다. 속성은 기본값 `[responsibilities, reports_to]` 입니다. 유지할까요?
>
> ✍️ **User:** `reports_to`는 빼고 `email` 넣어주세요.
>
> 💬 **Agent:** 알겠습니다. 지금 알고 있는 역할 2~3개 예시로 알려주시겠어요? (건너뛰어도 됩니다)
>
> ✍️ **User:** PM: 민수 / Eng-Lead: 지영 / Designer: 수빈
>
> ⚙️ **Action:** update ontology:
>
> ```yaml
> axes:
>   Actor:
>     active: true
>     default_classes:
>       Role: {properties: [responsibilities, email], folder: entities}
> ```
>
> 그리고 `wiki/entities/PM.md`, `Eng-Lead.md`, `Designer.md` 3개 seed 파일을 `class: Role` + `properties: {email, responsibilities}` 뼈대로 생성.

---

## Stage 2 — Activity Axis (WHAT HAPPENS)

**Purpose:** Define work units and temporal structure.

**Questions:**

1. "큰 단계(phase) 가 있나요? 있다면 순서대로 알려주세요.
    예) Discover → Design → Build → Validate → Release."
   - If yes: populate `workflow.phases` with `{id, order}`.
   - If no: leave `workflow.phases: []`.

2. "일상적으로 다루는 작업 단위가 뭔가요?
   - Task / Ticket / Story / Experiment / Sprint 등
   - 어떤 속성이 필요한가요? (owner, deadline, status, priority가 기본)"

3. "Meeting, Decision 로그를 남기나요?"
   - yes → activate Meeting, Decision
   - no → remove from defaults

4. "Event 클래스가 필요한가요? (예: 런칭일, 발표회, 컨퍼런스 등)"

**Output:** populated `axes.Activity.default_classes` and `workflow.phases`.

### Dialogue example

> 💬 **Agent:** 큰 단계(phase)가 있나요? software-project 기본 제안: **Discover → Design → Build → Validate → Release**.
>
> ✍️ **User:** 좀 달라요 — Design은 Build랑 겹쳐서 같이 가고, 그 대신 **Alpha → Beta → GA** 이렇게 가요. 앞에 Planning 하나 더요.
>
> 💬 **Agent:** 네, **Planning → Alpha → Beta → GA** 4단계로 기록합니다.
>
> ✍️ **User:** 그게 좋겠어요.
>
> 💬 **Agent:** 일상 작업 단위는요? 기본: **Task** — `[owner, status, deadline, priority]`.
>
> ✍️ **User:** 우리는 Jira 티켓 단위라 Ticket이 맞겠네요. 속성에 `ticket_id` 추가해주세요.
>
> 💬 **Agent:** `Task` 대신 `Ticket` 클래스로 저장하고 속성은 `[ticket_id, owner, status, deadline, priority]`.
>
> 💬 **Agent:** Meeting / Decision 로그를 남기시나요?
>
> ✍️ **User:** Decision만요. 회의록은 매번 남기기 부담스러워서.
>
> 💬 **Agent:** Event 클래스는요? (런칭일, 데모데이 같은 거요)
>
> ✍️ **User:** GA 런칭 이벤트가 있으니 넣어주세요.
>
> ⚙️ **Action:** update ontology:
>
> ```yaml
> axes:
>   Activity:
>     active: true
>     default_classes:
>       Ticket:   {properties: [ticket_id, owner, status, deadline, priority], folder: entities}
>       Phase:    {properties: [starts_at, ends_at, order], folder: entities}
>       Decision: {properties: [made_by, made_at, rationale, alternatives], folder: entities}
>       Event:    {properties: [date, type], folder: entities}
> workflow:
>   phases:
>     - {id: planning, order: 1}
>     - {id: alpha,    order: 2}
>     - {id: beta,     order: 3}
>     - {id: ga,       order: 4}
> ```

---

## Stage 3 — Artifact Axis (OUTPUTS)

**Purpose:** Define the documents and deliverables the project produces.

**Questions:**

1. "이 프로젝트에서 만들어지는 주요 산출물 유형은?
   기본 제공: Document, Deliverable, CodeArtifact, Design, Report.
   - 사용할 것 선택
   - 추가 커스텀 (예: Contract, Prototype, Dataset)"

2. "산출물에 life-cycle(상태)이 있나요?
   기본: draft → review → approved → published.
   - 그대로 사용 / 커스텀 / 생략"

3. "속성 확정 — 각 Artifact 클래스의 필수 필드를 확인하세요 (author, date, version, status 등)."

**Output:** populated `axes.Artifact.default_classes`.

### Dialogue example

> 💬 **Agent:** software-project 기본 산출물: **CodeArtifact, Deliverable, Document**. 여기에 디자인도 중요하니 **Design**을 추가 권장. Report는 잘 안 쓰일 것 같아 기본 제외했어요.
>
> ✍️ **User:** 네 그게 맞아요. Dataset은 없으니 추가 안 해도 돼요.
>
> 💬 **Agent:** 산출물 life-cycle(상태)은 기본 `draft → review → approved → published`인데, 코드 중심 프로젝트는 보통 `draft → review → merged → released` 쪽을 많이 쓰시는데 바꿀까요?
>
> ✍️ **User:** 후자가 맞아요. `released`는 사실상 태깅된 릴리즈고 merged는 PR 머지죠.
>
> 💬 **Agent:** CodeArtifact 속성은 기본 `[repo, path, owner, language]` — 추가·수정할 부분 있나요?
>
> ✍️ **User:** `pr_url` 추가해주세요. 어느 PR에서 나왔는지 보려고요.
>
> ⚙️ **Action:** update ontology:
>
> ```yaml
> axes:
>   Artifact:
>     active: true
>     default_classes:
>       CodeArtifact: {properties: [repo, path, owner, language, pr_url], folder: entities}
>       Deliverable:  {properties: [produced_by, consumed_by, status, acceptance_criteria], folder: entities}
>       Design:       {properties: [author, iteration, format], folder: entities}
>       Document:     {properties: [author, date, version, status], folder: entities}
>     lifecycle: [draft, review, merged, released]
> ```

---

## Stage 4 — Objective Axis (WHY)

**Purpose:** Goal hierarchy and risk tracking.

**Questions:**

1. "목표 계층이 있나요?
   기본 제공: Goal, Requirement, Milestone, KPI, Risk.
   - 전체 계층 사용 / 일부만 / 전부 생략"

2. (Goal이 활성화되면) "최상위 목표 1~3개를 알려주시겠어요? 나중에 추가해도 됩니다."

3. "Risk 추적이 필요한가요? (probability, impact, mitigation 속성이 기본으로 들어갑니다)"

**Output:** populated `axes.Objective.default_classes`, seed Goal pages in `wiki/concepts/` optionally.

### Dialogue example

> 💬 **Agent:** software-project 기본 목표 계층: **Requirement, Milestone**. Goal은 상위 개념(예: 제품 비전), KPI는 지표 중심. Risk는 별도 질문.
>
> ✍️ **User:** Goal은 있어야 해요 — "MVP to public launch"가 최상위 goal이에요. Requirement랑 Milestone도 다 써요. KPI는 데이터가 없으니 일단 제외.
>
> 💬 **Agent:** 최상위 Goal을 1~3개 등록해둘까요? 나중에 추가해도 됩니다.
>
> ✍️ **User:** "Ship QuickNotes GA by 2026-10-31", "5k DAU in 3 months post-launch" 두 개.
>
> 💬 **Agent:** Risk 추적은요? (probability/impact/mitigation 속성 자동 포함)
>
> ✍️ **User:** 네 필요해요. 5인 팀이라 리스크 관리가 중요하거든요.
>
> ⚙️ **Action:** update ontology and seed goal pages:
>
> ```yaml
> axes:
>   Objective:
>     active: true
>     default_classes:
>       Goal:        {properties: [parent_goal, target_date, metric, status], folder: concepts}
>       Requirement: {properties: [priority, source, status, acceptance_criteria], folder: concepts}
>       Milestone:   {properties: [date, exit_criteria, status], folder: concepts}
>       Risk:        {properties: [probability, impact, mitigation, owner], folder: concepts}
> ```
>
> 그리고 `wiki/concepts/ShipQuickNotesGA.md`, `5kDAUPostLaunch.md` 2개 seed 파일을 `class: Goal` + `properties: {target_date}` 로 생성.

---

## Stage 5 — Resource Axis (WITH WHAT)

**Purpose:** Budget, tools, assets. Default OFF.

**Questions:**

1. "예산을 추적하나요? (Budget 클래스 — amount, currency, period, owner)"
2. "도구/라이선스를 추적하나요? (Tool 클래스 — vendor, license, cost)"
3. "고정 자산을 추적하나요? (Asset 클래스 — type, location, owner)"

**If all three are no:** keep `axes.Resource.active: false`.
**If any yes:** set `active: true` and activate only the requested classes.

### Dialogue example

> 💬 **Agent:** Stage 0에서 Tool은 추적하겠다고 하셨죠. Budget과 Asset은요?
>
> ✍️ **User:** Budget은 회계팀 건이라 빼고, Asset도 없어요. Tool만요.
>
> 💬 **Agent:** Tool 속성 기본값은 `[vendor, license, cost, owner]`입니다. 그대로 쓸까요?
>
> ✍️ **User:** `cost`는 빼고 `url` 추가해주세요 — 각 서비스 링크 남기고 싶어서요.
>
> ⚙️ **Action:**
>
> ```yaml
> axes:
>   Resource:
>     active: true
>     default_classes:
>       Tool: {properties: [vendor, license, url, owner], folder: entities}
> ```

---

## Stage 6 — Context Axis (BACKGROUND)

**Purpose:** Domain / technology / constraints. Default OFF.

**Questions:**

1. "여러 도메인(산업/분야)을 넘나드는 프로젝트인가요? → Domain 클래스"
2. "기술 스택을 명시적으로 추적하나요? → Technology 클래스"
3. "외부 제약(법률, 규제, 시간)을 문서화해야 하나요? → Constraint 클래스"

Activate only what the user says yes to.

### Dialogue example

> 💬 **Agent:** software-project는 기본적으로 Technology 클래스 추천합니다. 단일 도메인이면 Domain은 필요 없고, Constraint는 컴플라이언스가 있을 때만.
>
> ✍️ **User:** SaaS라 개인정보보호(GDPR)는 대비해야 해요. Technology는 당연히 필요하고 Domain은 필요 없어요.
>
> 💬 **Agent:** Technology + Constraint 활성화합니다. Technology 속성 기본 `[category, version, vendor]` 유지?
>
> ✍️ **User:** 네.
>
> ⚙️ **Action:**
>
> ```yaml
> axes:
>   Context:
>     active: true
>     default_classes:
>       Technology: {properties: [category, version, vendor], folder: concepts}
>       Constraint: {properties: [type, source, hard_or_soft], folder: concepts}
> ```

---

## Stage 7 — Relations Confirmation

**Purpose:** Filter the default predicate vocabulary.

**Presentation:** Show a table of all predicates from `references/ontology-template.yaml`, with the ones whose `domain`/`range` reference only inactive classes **pre-marked as "hide"**.

Example (rendered to user):

```
Active predicates for your project:
  [✓] owns        (Actor → Activity/Artifact/Objective)
  [✓] produces    (Activity → Artifact)
  [✓] achieves    (Activity/Artifact → Objective)
  [✓] precedes    (Activity → Activity)
  [✓] authored_by (Artifact → Actor)
  [ ] consumes    — (Resource axis is off; hidden)
  [ ] reports_to  — (Role/hierarchy not used; hidden)

Add / remove predicates? Or add custom ones?
```

**Output:** finalized `relations:` block.

### Dialogue example

> 💬 **Agent:** 활성 예측 관계는 다음과 같이 제안합니다 — 제외/추가 있으신가요?
>
> ```
> [✓] owns         (Role → Ticket/CodeArtifact/Goal)
> [✓] produces     (Ticket → CodeArtifact/Deliverable)
> [✓] achieves     (Ticket/CodeArtifact → Goal/Milestone)
> [✓] precedes     (Ticket → Ticket)
> [✓] blocks       (Ticket → Ticket)
> [✓] authored_by  (Document/Design → Role)
> [✓] part_of      (any → any)
> [✓] requires     (Ticket → Technology/Tool)
> [ ] reports_to   — hidden (Role hierarchy 사용 안 함)
> [ ] consumes     — hidden (Budget 비활성)
> ```
>
> ✍️ **User:** `reviews` 관계 하나 추가할 수 있나요? PR 리뷰 관계 남기고 싶어요. Role → CodeArtifact.
>
> ⚙️ **Action:** add custom predicate:
>
> ```yaml
> relations:
>   reviews: {domain: [Actor], range: [CodeArtifact], inverse: reviewed_by}
> ```
>
> …plus the 8 pre-checked default predicates. Hidden predicates omitted.

---

## Stage 8 — Review & Save

1. Show the full assembled `ontology.yaml` to the user.
2. Ask: "저장할까요? (yes/no/edit <stage>)"
3. On yes:
   - Write `wiki/ontology.yaml` with the Write tool.
   - Generate `wiki/ontology-guide.md` — a human-readable summary of the ontology (one section per axis, listing active classes and their purpose).
   - Append to `wiki/log.md`:
     `## [YYYY-MM-DD] ontology-init | <N> classes, <M> relations, workflow=<phase_count>`
4. Output:
   ```
   ✅ Ontology saved to wiki/ontology.yaml
   ✅ Guide saved to wiki/ontology-guide.md
   Next: run /wiki-ingest — new ingests will use the ontology for context tagging.
   To revisit a stage: /wiki-ontology-init --edit <stage-name>
   ```

### Dialogue example

> 💬 **Agent:** 아래가 최종 ontology.yaml 입니다 (요약):
>
> ```
> project: QuickNotes (software-project, 2026-04-01 → 2026-10-31)
> axes:
>   Actor      (1 class):  Role
>   Activity   (4 classes): Ticket, Phase, Decision, Event
>   Artifact   (4 classes): CodeArtifact, Deliverable, Design, Document
>   Objective  (4 classes): Goal, Requirement, Milestone, Risk
>   Resource   (1 class):  Tool
>   Context    (2 classes): Technology, Constraint
> relations (9):  owns, produces, achieves, precedes, blocks, authored_by,
>                 part_of, requires, reviews
> workflow:  Planning → Alpha → Beta → GA
> ```
>
> 저장할까요? (yes / no / edit <stage>)
>
> ✍️ **User:** 좋아요, 저장해주세요.
>
> ⚙️ **Action:**
>
> 1. `Write` → `wiki/ontology.yaml` (full content from incremental saves)
> 2. Generate and `Write` → `wiki/ontology-guide.md`
> 3. Append to `wiki/log.md`:
>    `## [2026-04-21] ontology-init | 16 classes, 9 relations, workflow=4`
> 4. Print final summary:
>
>    ```
>    ✅ Ontology saved to wiki/ontology.yaml
>    ✅ Guide saved to wiki/ontology-guide.md
>    Active axes: Actor, Activity, Artifact, Objective, Resource, Context
>    Classes: 16 | Relations: 9 | Phases: 4
>    Next: /wiki-ingest will ask for document context on new ingests.
>    To revisit: /wiki-ontology-init --edit <stage-name>
>    ```

---

## `ontology-guide.md` Template

```markdown
# Ontology Guide — <Project Name>

> Human-readable summary of `wiki/ontology.yaml`. Auto-generated.
> Regenerate via `/wiki-ontology-init --regen-guide`.

## Project
- **Type:** <type>
- **Period:** <start> → <end>
- **Description:** <description>

## Active Axes

### Actor — Who
Active classes:
- **Team** — lead, members, domain
- **Role** — responsibilities, reports_to

(...repeat per active axis...)

## Workflow
<phase list in order, or "No fixed phases">

## Key Relations
- `owns` — Team owns Task (who's responsible)
- `produces` — Task produces Deliverable
- (...)

## How to Use
- Run `/wiki-ingest <file>` — you'll be asked to tag the document with
  phase, author, and related entities from this ontology.
- Run `/wiki-query class:Task AND context.phase=Build` — structural filter.
- Run `/wiki-ontology-validate` — check instances against the schema.
```
