"""Render the diagram sources to SVG through kroki.io and mermaid.ink: how corpus/svg/diagrams was made.

Usage: fetch_diagrams.py <out dir>. The services change over time, so a new run gives other bytes.
"""

import base64
import sys
import urllib.request
from pathlib import Path

OUT = Path(sys.argv[1])
UA = {"User-Agent": "svg-corpus/1.0", "Content-Type": "text/plain"}

MERMAID = {
    "flowchart": """flowchart TD
    A[Christmas] -->|Get money| B(Go shopping)
    B --> C{Let me think<br/>twice about it}
    C -->|One| D[Laptop with a <b>long</b> label that wraps]
    C -->|Two| E[iPhone]
    C -->|Three| F[fa:fa-car Car]
    subgraph S [Subgraph title]
      D --> G((Circle))
    end""",
    "sequence": """sequenceDiagram
    participant Alice
    participant Bob
    Alice->>John: Hello John, how are you?
    loop Healthcheck
        John->>John: Fight against hypochondria
    end
    Note right of John: Rational thoughts <br/>prevail!
    John-->>Alice: Great!
    John->>Bob: How about you?
    Bob-->>John: Jolly good!""",
    "class": """classDiagram
    Animal <|-- Duck
    Animal <|-- Fish
    Animal : +int age
    Animal : +String gender
    Animal: +isMammal()
    class Duck{
      +String beakColor
      +swim()
      +quack()
    }
    class Fish{
      -int sizeInFeet
      -canEat()
    }""",
    "state": """stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]""",
    "er": """erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses""",
    "gantt": """gantt
    title A Gantt Diagram
    dateFormat YYYY-MM-DD
    section Section
    A task           :a1, 2014-01-01, 30d
    Another task     :after a1  , 20d
    section Another
    Task in sec      :2014-01-12  , 12d
    another task     : 24d""",
    "pie": """pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15""",
    "mindmap": """mindmap
  root((mindmap))
    Origins
      Long history
      Popularisation
    Research
      On effectiveness<br/>and features
    Tools
      Pen and paper
      Mermaid""",
    "journey": """journey
    title My working day
    section Go to work
      Make tea: 5: Me
      Go upstairs: 3: Me
      Do work: 1: Me, Cat
    section Go home
      Go downstairs: 5: Me
      Sit down: 5: Me""",
    "gitgraph": """gitGraph
    commit
    branch develop
    checkout develop
    commit
    commit
    checkout main
    merge develop
    commit""",
}

KROKI = {
    "plantuml-sequence": (
        "plantuml",
        """@startuml
actor User
participant "Web Server" as WS
database DB
User -> WS : request
activate WS
WS -> DB : query
DB --> WS : rows
WS --> User : <b>response</b>
deactivate WS
note right of DB : a note\\nwith two lines
@enduml""",
    ),
    "plantuml-class": (
        "plantuml",
        """@startuml
class Car {
  - String model
  + drive()
}
interface Vehicle
Vehicle <|.. Car
Car *-- Wheel : 4
enum Color { RED\\n GREEN }
@enduml""",
    ),
    "plantuml-activity": (
        "plantuml",
        """@startuml
start
:Read the order;
if (All items in stock?) then (yes)
  :pack the items\\nand print the label;
else (no)
  :order from the supplier
  and mark the order as __waiting__;
endif
stop
@enduml""",
    ),
    "c4plantuml": (
        "c4plantuml",
        """!include <C4/C4_Container>
Person(user, "User", "A user of the system")
System_Boundary(c1, "Sample") {
  Container(web, "Web App", "Python", "Serves pages")
  ContainerDb(db, "Database", "PostgreSQL", "Stores data")
}
Rel(user, web, "Uses", "HTTPS")
Rel(web, db, "Reads/Writes")""",
    ),
    "graphviz": (
        "graphviz",
        """digraph G {
  rankdir=LR; node [shape=record];
  a [label="<in> input|<run> pro\\ cess|<out> output"];
  b [shape=ellipse, style=filled, fillcolor="#ffcc00", label="filled"];
  c [shape=box, style="rounded,dashed", label=<<b>HTML</b> <i>label</i>>];
  a:run -> b; a:out -> c; b -> c [color=red, penwidth=2];
}""",
    ),
    "bpmn": ("bpmn", None),
    "d2": (
        "d2",
        """shape: sequence_diagram
alice -> bob: What does it mean\\nto be well-adjusted?
bob -> alice: The ability to play bridge or\\ngolf as if they were games.
""",
    ),
    "d2-arch": (
        "d2",
        """direction: right
users: Users {shape: person}
lb: Load balancer
api: API {
  a: Service A
  b: Service B
}
db: Postgres {shape: cylinder}
users -> lb -> api.a
lb -> api.b
api.a -> db: SQL
api.b -> db""",
    ),
    "excalidraw": ("excalidraw", None),
    "nomnoml": (
        "nomnoml",
        """[Pirate|eyeCount: Int|raid();pillage()|
  [beard]--[parrot]
  [beard]-:>[foul mouth]
]
[<abstract>Marauder]<:--[Pirate]
[Pirate]- 0..7[mischief]""",
    ),
    "vegalite": (
        "vegalite",
        """{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {"values": [{"a": "A","b": 28},{"a": "B","b": 55},{"a": "C","b": 43},{"a": "D","b": 91}]},
  "mark": "bar",
  "encoding": {"x": {"field": "a","type": "nominal"},"y": {"field": "b","type": "quantitative"}}
}""",
    ),
    "wavedrom": (
        "wavedrom",
        """{ signal: [
  { name: "clk",  wave: "p.....|..." },
  { name: "Data", wave: "x.345x|=.x", data: ["head", "body", "tail", "data"] },
  { name: "Request", wave: "0.1..0|1.0" }
]}""",
    ),
    "svgbob": (
        "svgbob",
        """
    .---.     .-------.
   /     \\   | Hello  |---->
   \\     /   '-------'
    '---'        ^
                 |
     +-----------+
""",
    ),
    "blockdiag": (
        "blockdiag",
        """blockdiag {
  Order -> Pack -> Ship -> Deliver;
  Order -> Invoice -> Pay;
}""",
    ),
    "erd": (
        "erd",
        """[Person]
*name
height
weight
+birth_location_id

[Location]
*id
city
country

Person *--1 Location""",
    ),
    "pikchr": (
        "pikchr",
        """arrow right 150% "Plain" "Text"
box rad 8px "Text" "Parser" "(parse.c)" fit
arrow right 150% "Page" "Layout"
arrow <-> down 80% from last box.s
box same "Font" "Loader" "(fonts.c)" fit""",
    ),
    "structurizr": (
        "structurizr",
        """workspace {
  model {
    customer = person "Customer"
    shop = softwareSystem "Online Shop"
    payments = softwareSystem "Payment Provider"
    customer -> shop "Places orders"
    shop -> payments "Charges cards"
  }
  views {
    systemContext shop {
      include *
      autolayout lr
    }
  }
}""",
    ),
}

BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="d" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="p" isExecutable="false">
    <bpmn:startEvent id="s"/>
    <bpmn:task id="t" name="Review the request"/>
    <bpmn:endEvent id="e"/>
    <bpmn:sequenceFlow id="f1" sourceRef="s" targetRef="t"/>
    <bpmn:sequenceFlow id="f2" sourceRef="t" targetRef="e"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="dg"><bpmndi:BPMNPlane id="pl" bpmnElement="p">
    <bpmndi:BPMNShape id="s_di" bpmnElement="s"><dc:Bounds x="100" y="100" width="36" height="36"/></bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="t_di" bpmnElement="t"><dc:Bounds x="200" y="78" width="100" height="80"/></bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="e_di" bpmnElement="e"><dc:Bounds x="360" y="100" width="36" height="36"/></bpmndi:BPMNShape>
    <bpmndi:BPMNEdge id="f1_di" bpmnElement="f1"><di:waypoint x="136" y="118"/><di:waypoint x="200" y="118"/></bpmndi:BPMNEdge>
    <bpmndi:BPMNEdge id="f2_di" bpmnElement="f2"><di:waypoint x="300" y="118"/><di:waypoint x="360" y="118"/></bpmndi:BPMNEdge>
  </bpmndi:BPMNPlane></bpmndi:BPMNDiagram>
</bpmn:definitions>"""

EXCALIDRAW = """{"type":"excalidraw","version":2,"source":"x","elements":[
{"id":"a","type":"rectangle","x":10,"y":10,"width":200,"height":80,"angle":0,"strokeColor":"#1e1e1e","backgroundColor":"#a5d8ff","fillStyle":"hachure","strokeWidth":2,"strokeStyle":"solid","roughness":1,"opacity":100,"groupIds":[],"seed":1,"version":1,"versionNonce":1,"isDeleted":false,
 "boundElements":null,"updated":1,"link":null,"locked":false,"roundness":{"type":3}},
{"id":"b","type":"text","x":40,"y":35,"width":140,"height":25,"angle":0,"strokeColor":"#1e1e1e","backgroundColor":"transparent","fillStyle":"solid","strokeWidth":1,"strokeStyle":"solid","roughness":1,"opacity":100,"groupIds":[],"seed":2,"version":1,"versionNonce":1,"isDeleted":false,
 "boundElements":null,"updated":1,"link":null,"locked":false,"text":"Hand drawn","fontSize":20,"fontFamily":1,"textAlign":"left","verticalAlign":"top","baseline":18,"containerId":null,"originalText":"Hand drawn","lineHeight":1.25}
],"appState":{"viewBackgroundColor":"#ffffff"},"files":{}}"""


def post(url: str, body: str) -> bytes:
    req = urllib.request.Request(url, data=body.encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data: bytes = r.read()
        return data


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "svg-corpus/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data: bytes = r.read()
        return data


def save(name: str, data: bytes) -> None:
    (OUT / f"{name}.svg").write_bytes(data)
    print(f"{name}: {len(data)} bytes, foreignObject={data.count(b'<foreignObject')}")


for name, src in MERMAID.items():
    try:
        save(f"mermaid-ink-{name}", get("https://mermaid.ink/svg/" + base64.urlsafe_b64encode(src.encode()).decode()))
    except Exception as e:
        print(f"mermaid-ink-{name}: FAILED {e}")
    try:
        save(f"kroki-mermaid-{name}", post("https://kroki.io/mermaid/svg", src))
    except Exception as e:
        print(f"kroki-mermaid-{name}: FAILED {e}")

for name, (kind, given) in KROKI.items():
    source = given or (BPMN if kind == "bpmn" else EXCALIDRAW)
    try:
        save(f"kroki-{name}", post(f"https://kroki.io/{kind}/svg", source))
    except Exception as e:
        print(f"kroki-{name}: FAILED {e}")
