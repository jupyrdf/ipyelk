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


*** Keywords ***
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
