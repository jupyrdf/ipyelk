*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Resource            ../_resources/variables/Server.robot

Test Setup          Open Tool Probe
Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}tools
${TOOL A}       xpath:(//div[contains(@class,"tools-probe")]//div[contains(@class,"jp-ElkView")])[1]//*[substring(@id,string-length(@id)-7)='_tools-a']
${JS VIEWS}     return [...document.querySelectorAll('.tools-probe .jp-ElkView')].map(v => v.querySelector('svg > g').getAttribute('transform'));


*** Test Cases ***
Selection Before First Layout And Bidirectional Updates
    [Tags]    tool:selection    gh:165
    Tool Classes Should Be    tools-a    selected    2
    Run IPyElk Code In A New Cell    _tools.selection.ids = ()    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-a    selected    0
    ${node} =    Get WebElement    css:.tools-probe [id$="_tools-a"] > .elknode
    Execute Javascript    arguments[0].scrollIntoView({block:"center"})    ARGUMENTS    ${node}
    Click Element At Coordinates    ${node}    0    0
    Tool State Should Satisfy    state['selection'] == ['tools-a']
    Run IPyElk Code In A New Cell    _tools.selection.ids = ('tools-b',)    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-b    selected    2

Hover Enter Leave And Descendant Transitions
    [Tags]    tool:hover    gh:165
    Run IPyElk Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
    ${node} =    Get WebElement    css:.tools-probe [id$="_tools-a"] > .elknode
    Execute Javascript    arguments[0].scrollIntoView({block:"center"})    ARGUMENTS    ${node}
    Mouse Over    ${node}
    Tool State Should Satisfy    state['hovered'] == 'tools-a'
    ${label} =    Tool Element    tools-label    1
    Mouse Over    ${label}
    ${port} =    Tool Element    tools-port    1
    Mouse Over    ${port}
    Tool State Should Satisfy    state['hovered'] == 'tools-port' and None not in state['hover_changes']
    Mouse Over    css:.jp-NotebookPanel-toolbar
    Tool State Should Satisfy    state['hovered'] is None
    Run IPyElk Code In A New Cell    _tools.diagram.view.hover.hovered_id = 'tools-b'    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-b    hover    2
    Run IPyElk Code In A New Cell    _tools.diagram.view.hover.hovered_id = None    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-b    hover    0

Control Overlay Default Assignment And Removal
    [Tags]    tool:overlay    gh:165
    # Deliberately unconditional: this gates oldest as well as newest frontend.
    Page Should Not Contain Element    css:.tools-probe [id*="_entropy"]
    Run IPyElk Code In A New Cell    _tools.overlay()    screen=${EMPTY}
    Wait Until Page Contains Element
    ...    xpath://div[contains(@class,'tools-probe')]//button[normalize-space()='tools-overlay']
    ...    timeout=30s
    Run IPyElk Code In A New Cell    _tools.diagram.view.control_overlay = None    screen=${EMPTY}
    Wait Until Page Does Not Contain Element
    ...    xpath://div[contains(@class,'tools-probe')]//button[normalize-space()='tools-overlay']
    ...    timeout=30s

Viewport Wheel Reports Originating View And Coalesces Burst
    [Tags]    tool:viewport    gh:165
    ${before} =    Execute Javascript    ${JS VIEWS}
    Run IPyElk Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
    Execute Javascript
    ...    const v=document.querySelectorAll('.tools-probe .sprotty-root')[0]; for(let i=0;i<10;i++) v.dispatchEvent(new WheelEvent('wheel',{altKey:true,deltaX:5,deltaY:7,bubbles:true}));
    Tool State Should Satisfy    len(state['camera_changes']) == 1 and len(state['camera_updates']) == 1
    ${state} =    Tool State
    ${view id} =    Set Variable    ${state}[camera_id]
    ${after} =    Execute Javascript    ${JS VIEWS}
    Should Not Be Equal    ${before}[0]    ${after}[0]
    Should Be Equal    ${before}[1]    ${after}[1]
    Sleep    1s
    Tool State Should Satisfy
    ...    len(state['camera_changes']) == 1 and len(state['camera_updates']) == 1 and state['camera_changes'][0]['view'] == '${view id}'

Viewport Drag Reports Originating View
    [Tags]    tool:viewport    gh:165
    ${before} =    Execute Javascript    ${JS VIEWS}
    Run IPyElk Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
    ${canvas} =    Get WebElement    css:.tools-probe .sprotty-root
    Execute Javascript    arguments[0].scrollIntoView({block:'center'})    ARGUMENTS    ${canvas}
    Drag And Drop By Offset    ${canvas}    35    20
    Tool State Should Satisfy    len(state['camera_changes']) == 1 and len(state['camera_updates']) == 1
    ${after} =    Execute Javascript    ${JS VIEWS}
    Should Not Be Equal    ${before}[0]    ${after}[0]
    Should Be Equal    ${before}[1]    ${after}[1]

Viewport Targeted And Broadcast Commands
    [Tags]    tool:viewport    gh:165
    # Produce a report so the target id is obtained from the public kernel API.
    Execute Javascript
    ...    document.querySelectorAll('.tools-probe .sprotty-root')[0].dispatchEvent(new WheelEvent('wheel',{altKey:true,deltaX:8,deltaY:9,bubbles:true}));
    Tool State Should Satisfy    state['camera_id'] is not None
    ${state} =    Tool State
    ${before} =    Execute Javascript    ${JS VIEWS}
    Run IPyElk Code In A New Cell
    ...    _tools.diagram.view.set_viewport(origin=(31, 43), zoom=0.75, animate=False, view_id='${state}[camera_id]')
    ...    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Target Camera Should Move    ${before}
    Run IPyElk Code In A New Cell
    ...    _tools.diagram.view.set_viewport(origin=(17, 23), zoom=0.9, animate=False)
    ...    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Cameras Should Match

Painter All Views Relayout Export Purity And Clear
    [Tags]    tool:painter    gh:165
    ${before} =    Tool State
    Run IPyElk Code In A New Cell    _tools.diagram.view.painter.paint('tools-a', 'tools-painted')    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-a    tools-painted    2
    Tool State Should Satisfy    state['elk'] == ${before}[elk] and 'tools-painted' not in json.dumps(state['source'])
    Run IPyElk Code In A New Cell    await _tools.relayout()    screen=${EMPTY}
    Tool Classes Should Be    tools-a    tools-painted    2
    Run IPyElk Code In A New Cell    _tools.export()    screen=${EMPTY}
    Wait Until Keyword Succeeds    30x    0.5s    Export Should Include Paint
    Run IPyElk Code In A New Cell    _tools.diagram.view.painter.clear()    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-a    tools-painted    0
    Tool Classes Should Be    tools-a    tools-model-class    2

Collapse Avoids Text Requests And Validation
    [Tags]    tool:substrate    gh:165
    Run IPyElk Code In A New Cell    await _tools.collapse(); print('TOOLS-COLLAPSE-PASS')    screen=${EMPTY}
    Wait Until Page Contains    TOOLS-COLLAPSE-PASS
    Page Should Not Contain Contain Standard Errors

Ten Refreshes Cost Exactly One Layout
    [Tags]    tool:substrate    gh:165
    Run IPyElk Code In A New Cell    await _tools.refresh_burst(); print('TOOLS-BURST-PASS')    screen=${EMPTY}
    Wait Until Page Contains    TOOLS-BURST-PASS
    Page Should Not Contain Contain Standard Errors

Headless Full Refresh Completes
    [Tags]    tool:substrate    gh:165
    Run IPyElk Code In A New Cell    await _tools.headless(); print('TOOLS-HEADLESS-PASS')    screen=${EMPTY}
    Wait Until Page Contains    TOOLS-HEADLESS-PASS    timeout=20s
    Page Should Not Contain Contain Standard Errors


*** Keywords ***
Open Tool Probe
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    Copy File    ${FIXTURES}${/}tool_probe.py    ${OUTPUT DIR}${/}home${/}tool_probe.py
    Run IPyElk Code In A New Cell    _tools = __import__('tool_probe').Probe(); await _tools.ready()    screen=${EMPTY}
    Page Should Not Contain Contain Standard Errors
    Wait Until Keyword Succeeds    30x    0.5s    Tool Classes Should Be    tools-a    selected    2

Tool Element
    [Arguments]    ${id}    ${index}
    ${element} =    Get WebElement
    ...    xpath:(//div[contains(@class,'tools-probe')]//div[contains(@class,'jp-ElkView')])[${index}]//*[substring(@id,string-length(@id)-string-length('${id}'))='_${id}']
    RETURN    ${element}

Tool Classes Should Be
    [Arguments]    ${id}    ${class}    ${count}
    ${selector} =    Set Variable    .tools-probe [id$="_${id}"].${class}
    IF    "${class}" == "hover"
        ${selector} =    Set Variable    .tools-probe [id$="_${id}"] > .elknode.mouseover
    END
    ${found} =    SeleniumLibrary.Get Element Count    css:${selector}
    Should Be Equal As Integers    ${found}    ${count}

Tool State
    # Query without scrolling or moving the pointer off the diagram under test.
    ${token} =    Evaluate    'TOOLSx' + secrets.token_hex(5)    secrets
    Execute Javascript
    ...    window.toolProbeAnswers ??= {}; const token=arguments[0]; const f=window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.requestExecute({code:"_tools.report('"+token+"')"}); f.onIOPub=m=>{if(m.header.msg_type==='stream' && m.content.text.startsWith(token+' ')) window.toolProbeAnswers[token]=JSON.parse(m.content.text.slice(token.length+1));};
    ...    ARGUMENTS
    ...    ${token}
    Wait For Condition    return window.toolProbeAnswers?.['${token}'] != null    timeout=30s
    ${state} =    Execute Javascript
    ...    const answer=window.toolProbeAnswers[arguments[0]]; delete window.toolProbeAnswers[arguments[0]]; return answer;
    ...    ARGUMENTS
    ...    ${token}
    RETURN    ${state}

Tool State Should Satisfy
    [Arguments]    ${expression}
    Wait Until Keyword Succeeds    20x    0.25s    Tool State Should Really Satisfy    ${expression}

Tool State Should Really Satisfy
    [Arguments]    ${expression}
    ${state} =    Tool State
    ${satisfied} =    Evaluate    eval($expression, {'state': $state, 'json': json})    json
    Should Be True    ${satisfied}    ${expression}: ${state}

Target Camera Should Move
    [Arguments]    ${before}
    ${after} =    Execute Javascript    ${JS VIEWS}
    Should Not Be Equal    ${before}[0]    ${after}[0]
    Should Be Equal    ${before}[1]    ${after}[1]

Cameras Should Match
    ${views} =    Execute Javascript    ${JS VIEWS}
    Should Be Equal    ${views}[0]    ${views}[1]

Export Should Include Paint
    Tool State Should Satisfy    state['export_ready']
    Run IPyElk Code In A New Cell    _tools.assert_export(); print('TOOLS-EXPORT-PASS')    screen=${EMPTY}
    Wait Until Page Contains    TOOLS-EXPORT-PASS    timeout=2s
    Page Should Not Contain Contain Standard Errors
