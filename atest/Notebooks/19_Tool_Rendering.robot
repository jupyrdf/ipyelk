*** Settings ***
Resource            ../_resources/keywords/Tools.robot

Test Setup          Open Tool Probe
Test Teardown       Clean up after IPyElk Example


*** Test Cases ***
Painter All Views Relayout Export Purity And Clear
    [Tags]    tool:painter    gh:165
    ${before} =    Tool State
    Run Tool Code In A New Cell    _tools.diagram.view.painter.paint('tools-a', 'tools-painted')    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-a    tools-painted    2
    Tool State Should Satisfy    state['elk'] == ${before}[elk] and 'tools-painted' not in json.dumps(state['source'])
    Start Tool Operation And Wait    relayout
    Tool Classes Should Be    tools-a    tools-painted    2
    Run Tool Code In A New Cell    _tools.export()    screen=${EMPTY}
    Wait Until Keyword Succeeds    30x    0.5s    Export Should Include Paint
    Run Tool Code In A New Cell    _tools.diagram.view.painter.clear()    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-a    tools-painted    0
    Tool Classes Should Be    tools-a    tools-model-class    2

Collapse Avoids Text Requests And Validation
    [Tags]    tool:substrate    gh:165
    Start Tool Operation And Wait    collapse
    Page Should Not Contain Contain Standard Errors

Ten Refreshes Cost Exactly One Layout
    [Tags]    tool:substrate    gh:165
    Start Tool Operation And Wait    refresh_burst
    Page Should Not Contain Contain Standard Errors

Headless Full Refresh Completes
    [Tags]    tool:substrate    gh:165
    Start Tool Operation And Wait    headless
    Page Should Not Contain Contain Standard Errors
