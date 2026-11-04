*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Resource            ../_resources/variables/Server.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}00_Introduction
${FIT PROBE}    fit_probe.py
# the n-th last Elk view's content box against its canvas, in CSS pixels
${JS FIT}
...             const views = [...document.querySelectorAll("${CSS ELK VIEW}")];
...             const view = views[views.length - arguments[0]];
...             view.scrollIntoView({block: "center"});
...             const svg = view.querySelector("svg${CSS SPROTTY GRAPH}");
...             const s = svg.getBoundingClientRect();
...             const c = svg.querySelector(":scope > g").getBoundingClientRect();
...             return {canvas: [s.width, s.height],
...             dx: c.left + c.width / 2 - (s.left + s.width / 2),
...             dy: c.top + c.height / 2 - (s.top + s.height / 2),
...             fill: Math.max(c.width / s.width, c.height / s.height)};
# a mouseover on one node label in each of the first two Elk views, in one script
${JS HOVER}
...             const views = [...document.querySelectorAll("${CSS ELK VIEW}")];
...             const label = (view, text) => [...view.querySelectorAll(".elklabel")]
...             .find((el) => el.textContent.trim() === text);
...             label(views[0], "kernel").dispatchEvent(new MouseEvent("mouseover", {bubbles: true}));
...             label(views[1], "model").dispatchEvent(new MouseEvent("mouseover", {bubbles: true}));


*** Test Cases ***
00_Introduction
    [Tags]    data:simple.json    gh:6
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    Elk Counts Should Be    &{SIMPLE COUNTS}
    Linked Elk Output Counts Should Be    &{SIMPLE COUNTS}
    Custom Elk Selectors Should Exist    @{SIMPLE CUSTOM}

00_Introduction Fit On First Layout
    [Documentation]    A diagram displayed only after its first layout fits each
    ...    view in the browser (``fit_on_first_layout``): a ``fit()`` from the
    ...    kernel would have reached no view. The view in a collapsed accordion
    ...    is hidden at its first layout and fits when the accordion opens.
    [Tags]    data:simple.json    gh:245    tool:fit
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    Copy File    ${FIXTURES}${/}${FIT PROBE}    ${OUTPUT DIR}${/}home${/}${FIT PROBE}
    Run IPyElk Code In A New Cell
    ...    _fp = __import__("fit_probe"); _fit = _fp.Probe(a_simple_elk_json_example(view=_fp.view()))
    ...    screen=50-built.png
    Wait Until Keyword Succeeds    30x    1s    Fit Probe Should Be Laid Out
    Run IPyElk Code In A New Cell    _fit.show()    screen=51-shown.png
    Wait Until Keyword Succeeds    20x    0.5s    Elk View Should Be Fitted    2
    Capture Page Screenshot    52-shown-view-fitted.png
    Click Element    xpath:(//*[contains(@class, "jupyter-widget-Collapse-header")])[last()]
    Wait Until Keyword Succeeds    20x    0.5s    Elk View Should Be Fitted    1
    Capture Page Screenshot    53-revealed-view-fitted.png

00_Introduction Hover In Two Views Of One Diagram
    [Documentation]    One ``Diagram`` displayed twice has two views of one
    ...    viewer model. Hovers in both views must leave a page that still
    ...    answers, and a ``hover.hovered_id`` that stops changing in the kernel.
    ...    A view used to write the feedback that it replays from
    ...    ``hovered_id`` back to it, and late feedback looped without end.
    [Tags]    data:simple.json    tool:hover
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    Run IPyElk Code In A New Cell
    ...    _hc = []; simple.view.hover.observe(lambda c: _hc.append(c["new"]), "hovered_id"); display(simple)
    ...    screen=60-displayed-twice.png
    Wait Until Keyword Succeeds    30x    1s    Elk Counts Should Really Be    &{SIMPLE COUNTS}    n=${2}
    ...    screen=61-two-views.png
    # two hovers in one tick, one in each view: the feedback replays land late
    Execute Javascript    ${JS HOVER}
    FOR    ${round}    IN RANGE    3
        Hover Elk Node    kernel    1
        Hover Elk Node    view    2
        Hover Elk Node    model    1
        Hover Elk Node    sprotty    2
        Hover Elk Node    YOU    1
        Hover Elk Node    kernel    2
    END
    Mouse Over    css:.jp-NotebookPanel-toolbar
    Capture Page Screenshot    62-hovered.png
    ${first} =    Get Hover State
    Sleep    2s
    ${second} =    Get Hover State
    Should Be Equal    ${first}    ${second}    hovered_id still changes in the kernel    values=${TRUE}
    Should Be True    $second["id"] is None    the pointer left the diagrams: ${second}
    Capture Page Screenshot    63-settled.png


*** Keywords ***
Hover Elk Node
    [Documentation]    Move the pointer over the label of ``${node}`` in the
    ...    ``${index}``-th Elk view.
    [Arguments]    ${node}    ${index}
    ${label} =    Get WebElement
    ...    xpath:(//div[contains(@class,"jp-ElkView")])[${index}]//*[contains(@class,"elklabel")][normalize-space()="${node}"]
    Execute Javascript    arguments[0].scrollIntoView({block: "center", inline: "center"})    ARGUMENTS    ${label}
    Mouse Over    ${label}

Get Hover State
    [Documentation]    The kernel's ``hovered_id`` and how often it changed, from
    ...    a new cell. A page that a feedback loop starves cannot run the cell.
    ${token} =    Evaluate    "ELKHOVERx%s" % secrets.token_hex(4)    secrets
    Run IPyElk Code In A New Cell
    ...    print("${token}", json.dumps({"id": simple.view.hover.hovered_id, "changes": len(_hc)}))
    ...    screen=${EMPTY}
    ${xp} =    Set Variable    xpath://*[contains(@class, "jp-OutputArea-output")][contains(., "${token} ")]
    Wait Until Page Contains Element    ${xp}    timeout=30s
    ${out} =    Get Text    ${xp}
    ${state} =    Evaluate    json.loads($out.split(" ", 1)[1])    json
    Log    ${state}
    RETURN    ${state}

Fit Probe Should Be Laid Out
    ${token} =    Evaluate    "ELK245x%s" % secrets.token_hex(4)    secrets
    Run IPyElk Code In A New Cell    _fit.report("${token}")    screen=${EMPTY}
    ${xp} =    Set Variable    xpath://*[contains(@class, "jp-OutputArea-output")][contains(., "${token} ")]
    Wait Until Page Contains Element    ${xp}    timeout=10s
    ${out} =    Get Text    ${xp}
    ${state} =    Evaluate    json.loads($out.split(" ", 1)[1])    json
    Should Be True    $state["laid_out"]    the diagram has not been laid out yet

Elk View Should Be Fitted
    [Documentation]    The ``${nth last}`` Elk view frames the whole diagram: the
    ...    content is centred on the canvas and fills it along one axis, less
    ...    the probe's padding. A view left at 1:1 sits in the top-left corner.
    [Arguments]    ${nth last}
    ${fit} =    Execute Javascript    ${JS FIT}    ARGUMENTS    ${nth last}
    Log    ${fit}
    Should Be True    $fit["canvas"][0] > 100 and $fit["canvas"][1] > 100    the view has no size: ${fit}
    Should Be True    abs($fit["dx"]) < 15 and abs($fit["dy"]) < 15    the diagram is off centre: ${fit}
    Should Be True    0.8 < $fit["fill"] < 1.02    the diagram does not fill the view: ${fit}
