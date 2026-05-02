# scala Roadmap


### 1. Related roadmap 정보 및 다른 roadmap 파일과의 관계성
이 로드맵은 Scala 학습과 연관되어 있거나, 학습 전후로 계속해서 참고하기 좋은 다른 로드맵으로 다음 네 가지를 제시하고 있습니다.
*   **Backend (백엔드) 로드맵**
*   **Data Engineer (데이터 엔지니어) 로드맵**
*   **MLOps 로드맵**
*   **Java 로드맵**

### 2. 로드맵 구성요소간 전후관계 및 세부 구성 항목
Scala 로드맵의 전반적인 흐름은 언어 소개 및 개발 환경 설정으로 시작하여, 언어의 핵심 문법과 구조를 다루는 '기본기 학습(Learn the Basics)', 이후 '도구 및 생태계(Tools, Ecosystem & Platforms)', '프레임워크 및 라이브러리', '심화 주제(Advanced Topics)'로 뻗어나가는 구조를 갖추고 있습니다. 

각 단계와 세부 항목은 다음과 같습니다.

#### 단계 1: 소개 및 환경 설정 (Introduction & Setting Up Scala)
*   **Introduction (소개):** Docs(문서), Courses(강의), Books(도서), YouTube.
*   **Setting Up Scala (환경 설정):** 
    *   Pick your IDE (주요 IDE): IntelliJ IDEA, VS Code, Vim, Zed.
    *   Secondary Options (보조 옵션): Emacs, Sublime.

#### 단계 2: 기본기 학습 (Learn the Basics)
*   **문법 기초 및 제어문:** Variables & Constants(변수와 상수), Operators(연산자), Conditionals(조건문), Loops(반복문), Try/Catch.
*   **객체 지향 개념:** Object(객체), Class(클래스), Trait(트레이트).
*   **데이터 타입 및 제네릭:** 
    *   Main Data Types: Integers, Strings, Booleans, Unit, Float, Nothing.
    *   Generic Types: Type Hierarchy, Type Parameters, Conversions.
*   **자료구조 및 컬렉션 (Data Structures):** 
    *   Array, Seq, Range, List, Vector, Set, Map, Mutable Collections.
*   **함수 및 메서드 (Functions & Methods):** Method Calls, Anonymous Func / Lambda(익명 함수/람다), Total/Partial Funcs, Funcs returning Funcs.
*   **컬렉션 및 문자열 다루기:** 
    *   Common Collection Methods: collect / collectFirst, find, filter, flatMap, foldLeft, foreach, map.
    *   Working with Strings: Regex(정규표현식).
*   **패턴 매칭 (Pattern Matching):** Case Classes, Sealed Traits, apply Method, Enums, Case Objects, unapply Method.
*   **에러 처리 및 지연 평가:**
    *   Error Handling: Option, Either, Try, for comprehension.
    *   Laziness (지연 평가): Lazy vals, by-name Parameters, Lazy Collections(Iterators, Views, LazyList).
*   **기타 기본기:** 
    *   Scope & Visibility: private / protected, package, Implicit Parameter.
    *   Recursion (재귀): Tail Recursion, Trampolines.
    *   Early returns.

#### 단계 3: 도구, 생태계 및 플랫폼 (Tools, Ecosystem & Platforms)
*   **Build Tools (빌드 도구):** 
    *   Scala-centered (Scala 중심): ScalaCLI, sbt, Mill.
    *   Common to JVM (JVM 공통): Gradle, Maven.
*   **Ecosystems (생태계):** Cats, ZIO, Li Haoyi, Akka / Pekko, No Ecosystem.
*   **Platforms (플랫폼):** JVM, Scala Native, Scala.js.

#### 단계 4: 프레임워크 및 라이브러리 (Frameworks and Libraries)
*   **Testing (테스트):** 
    *   Unit Testing: ScalaTest, mUnit, uTest, JUnit, ZIO Test, specs2.
    *   Integration / Performance Testing: ScalaTest, Gatling.
*   **Effect Systems:** Cats Effect, ZIO.
*   **Backend (백엔드):** Scalatra, sttp, AkkaHTTP, Play, Tapir, http4s.
*   **GUI (그래픽 사용자 인터페이스):** 
    *   Web: Slinky, Calico, Laminar, React.js.
    *   Desktop: ScalaFX, JavaFX.
    *   Android: scala-android-plugin, Scala on Android.
*   **Concurrency (동시성):** Ox, Gears, Streaming(FS2, Kyo, Akka & Peko Streams, ZIO Streams).
*   **Distributed Computing (분산 컴퓨팅):** Spark, Akka, Pekko.
*   **Data Handling (데이터 처리):** 
    *   Database: Slick, ScalikeJDBC, Doobie, Quill.
    *   JSON: PlayJSON, Circe, Jsoniter, uPickle.
*   **추가 분야:** Video game Engines (Indigo, CosPlay, LibGDX w/ Scala), GraalVM Native Image.

#### 단계 5: 심화 주제 (Advanced Topics)
*(참고: 심화 주제는 순차적으로 배울 필요 없이 프레임워크나 라이브러리를 탐색하며 필요할 때 학습하는 것을 권장합니다.)*
*   Referential Transparency(참조 투명성), Pure Functions(순수 함수).
*   Monads(모나드), Category Theory(카테고리 이론).
*   Capture Checking, Capabilities.
*   Variance, Context Bounds.
*   **Type System (타입 시스템) & Macros:** Typeclasses, Macros. 관련 라이브러리로는 Monocle, Shapeless, Chimney, Scalameta, Magnolia가 있습니다.