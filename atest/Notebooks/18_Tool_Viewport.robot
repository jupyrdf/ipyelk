*** Settings ***
Resource            ../_resources/keywords/Tools.robot

Test Setup          Open Tool Probe
Test Teardown       Clean up after IPyElk Example


*** Test Cases ***
Viewport Wheel Reports Originating View And Coalesces Burst
    [Tags]    tool:viewport    gh:165
    ${before}    ${sizes before} =    Prepare Tool Viewport Gesture
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
    ${sizes after} =    Tool Canvas Sizes
    Should Be Equal    ${sizes before}    ${sizes after}    the wheel burst must not resize its canvas

Viewport Drag Reports Originating View
    [Tags]    tool:viewport    gh:165
    ${before}    ${sizes before} =    Prepare Tool Viewport Gesture
    ${canvas} =    Get WebElement    css:.tools-probe .sprotty-root
    Drag And Drop By Offset    ${canvas}    35    20
    Tool State Should Satisfy    len(state['camera_changes']) == 1 and len(state['camera_updates']) == 1
    ${after} =    Execute Javascript    ${JS VIEWS}
    Should Not Be Equal    ${before}[0]    ${after}[0]
    Should Be Equal    ${before}[1]    ${after}[1]
    ${sizes after} =    Tool Canvas Sizes
    Should Be Equal    ${sizes before}    ${sizes after}    the gesture must not resize its canvas
    Sleep    1s
    Tool State Should Satisfy    len(state['camera_changes']) == 1 and len(state['camera_updates']) == 1
    ${sizes late} =    Tool Canvas Sizes
    Should Be Equal    ${sizes before}    ${sizes late}    the settled canvas must remain unchanged

Viewport Targeted And Broadcast Commands
    [Tags]    tool:viewport    gh:165
    # Wait for this wheel report, rather than accepting either view's initial
    # snapshot. Keep its public view id even if another view reports afterward.
    Run Tool Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
    Execute Javascript
    ...    document.querySelectorAll('.tools-probe .sprotty-root')[0].dispatchEvent(new WheelEvent('wheel',{altKey:true,deltaX:8,deltaY:9,bubbles:true}));
    Tool State Should Satisfy    any(r['origin'] == [8, 9] and r['zoom'] == 1 for r in state['camera_changes'])
    ${state} =    Tool State
    ${view id} =    Evaluate
    ...    next(r['view'] for r in $state['camera_changes'] if r['origin'] == [8, 9] and r['zoom'] == 1)
    ${before} =    Execute Javascript    ${JS VIEWS}
    Run Tool Code In A New Cell
    ...    _tools.diagram.view.set_viewport(origin=(31, 43), zoom=0.75, animate=False, view_id='${view id}')
    ...    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Target Camera Should Move    ${before}
    Run Tool Code In A New Cell
    ...    _tools.diagram.view.set_viewport(origin=(17, 23), zoom=0.9, animate=False)
    ...    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Cameras Should Match
