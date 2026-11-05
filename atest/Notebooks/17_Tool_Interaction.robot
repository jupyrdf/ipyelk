*** Settings ***
Resource            ../_resources/keywords/Tools.robot

Test Setup          Open Tool Probe
Test Teardown       Clean up after IPyElk Example


*** Test Cases ***
Selection Before First Layout And Bidirectional Updates
    [Tags]    tool:selection    gh:165
    Tool Classes Should Be    tools-a    selected    2
    Run Tool Code In A New Cell    _tools.selection.ids = ()    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-a    selected    0
    ${node} =    Get WebElement    css:.tools-probe [id$="_tools-a"] > .elknode
    Execute Javascript    arguments[0].scrollIntoView({block:"center"})    ARGUMENTS    ${node}
    Click Element At Coordinates    ${node}    0    0
    Tool State Should Satisfy    state['selection'] == ['tools-a']
    Run Tool Code In A New Cell    _tools.selection.ids = ('tools-b',)    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-b    selected    2

Hover Enter Leave And Descendant Transitions
    [Tags]    tool:hover    gh:165
    Run Tool Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
    ${node} =    Get WebElement    css:.tools-probe [id$="_tools-a"] > .elknode
    Execute Javascript    arguments[0].scrollIntoView({block:"center"})    ARGUMENTS    ${node}
    Mouse Over    ${node}
    Tool State Should Satisfy    state['hovered'] == 'tools-a'
    ${label} =    Tool Element    tools-label    1
    Mouse Over    ${label}
    Tool State Should Satisfy    state['hovered'] == 'tools-a' and None not in state['hover_changes']
    # Return through the node body and then horizontally onto its side port:
    # continuity must not depend on interpolation of a diagonal trajectory.
    Mouse Over    ${node}
    ${port} =    Tool Element    tools-port    1
    Mouse Over    ${port}
    Tool State Should Satisfy    state['hovered'] == 'tools-port' and None not in state['hover_changes']
    Mouse Over    css:.jp-NotebookPanel-toolbar
    Tool State Should Satisfy    state['hovered'] is None
    Run Tool Code In A New Cell    _tools.diagram.view.hover.hovered_id = 'tools-b'    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-b    hover    2
    Run Tool Code In A New Cell    _tools.diagram.view.hover.hovered_id = None    screen=${EMPTY}
    Wait Until Keyword Succeeds    20x    0.25s    Tool Classes Should Be    tools-b    hover    0

Control Overlay Default Assignment And Removal
    [Tags]    tool:overlay    gh:165
    # Deliberately unconditional: this gates oldest as well as newest frontend.
    Page Should Not Contain Element    css:.tools-probe [id*="_entropy"]
    Run Tool Code In A New Cell    _tools.overlay()    screen=${EMPTY}
    Wait Until Page Contains Element
    ...    xpath://div[contains(@class,'tools-probe')]//button[normalize-space()='tools-overlay']
    ...    timeout=30s
    Run Tool Code In A New Cell    _tools.diagram.view.control_overlay = None    screen=${EMPTY}
    Wait Until Page Does Not Contain Element
    ...    xpath://div[contains(@class,'tools-probe')]//button[normalize-space()='tools-overlay']
    ...    timeout=30s
