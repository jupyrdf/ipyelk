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

Viewport Wheel Reports Originating View And Coalesces Burst
    [Tags]    tool:viewport    gh:165
    ${before} =    Execute Javascript    ${JS VIEWS}
    Run Tool Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
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
    Run Tool Code In A New Cell    _tools.reset_events()    screen=${EMPTY}
    ${canvas} =    Get WebElement    css:.tools-probe .sprotty-root
    Execute Javascript    arguments[0].scrollIntoView({block:'center'})    ARGUMENTS    ${canvas}
    Drag And Drop By Offset    ${canvas}    35    20
    Tool State Should Satisfy    len(state['camera_changes']) == 1 and len(state['camera_updates']) == 1
    ${after} =    Execute Javascript    ${JS VIEWS}
    Should Not Be Equal    ${before}[0]    ${after}[0]
    Should Be Equal    ${before}[1]    ${after}[1]

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


*** Keywords ***
Open Tool Probe
    Open Tool Introduction
    Execute Javascript    window.toolProbeTransport={failure:null,answers:{}};
    Copy File    ${FIXTURES}${/}tool_probe.py    ${OUTPUT DIR}${/}home${/}tool_probe.py
    Run Tool Code In A New Cell    _tools = __import__('tool_probe').Probe()    screen=${EMPTY}
    Wait Until Tool Operation Finishes    ready
    Page Should Not Contain Contain Standard Errors
    Wait Until Keyword Succeeds    30x    0.5s    Tool Classes Should Be    tools-a    selected    2

Open Tool Introduction
    Set Screenshot Directory    ${SCREENS}${/}${INTRODUCTION.lower()}
    Set Tags    notebook:${INTRODUCTION}
    ${files} =    Get All IPyElk Example Paths
    Copy Support Files    ${files}
    # Open the requested document directly. A context-menu race once left the
    # all-Markdown index active, so kernel-idle alone cannot establish readiness.
    Execute Javascript
    ...    window.toolNotebookOpen={done:false}; const app=window.jupyterapp; app.commands.execute('docmanager:open',{path:'${INTRODUCTION}.ipynb',factory:'Notebook'}).then(async panel=>{await panel.context.ready; await panel.revealed; app.shell.activateById(panel.id); window.toolNotebookOpen={done:true};}).catch(error=>{window.toolNotebookOpen={done:true,error:String(error)};});
    Wait For Condition    return window.toolNotebookOpen.done    timeout=30s
    ${error} =    Execute Javascript    return window.toolNotebookOpen.error || null;
    Should Be Equal    ${error}    ${None}
    Tool Notebook Should Be Active    ${INTRODUCTION}.ipynb
    Capture Page Screenshot    00-opened.png
    Wait Until Element Is Visible    ${JLAB XP KERNEL IDLE}    timeout=30s
    Lab Command    Clear Outputs of All Cells
    Ensure Sidebar Is Closed
    Capture Page Screenshot    01-loaded.png
    Elk Counts Should Be
    Restart and Run All
    Wait For All Cells To Run    300s
    Capture Each Cell Output    09-
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    10-ran-all-without-stderr.png

Tool Notebook Should Be Active
    [Arguments]    ${path}
    ${active} =    Execute Javascript    return window.jupyterapp.shell.currentWidget?.context?.path;
    Should Be Equal    ${active}    ${path}    the active notebook must be the requested tool-test host

Start Tool Operation And Wait
    [Arguments]    ${operation}
    Run Tool Code In A New Cell    _tools.start('${operation}')    screen=${EMPTY}
    Wait Until Tool Operation Finishes    ${operation}

Wait Until Tool Operation Finishes
    [Arguments]    ${operation}
    # The cell must return first: browser-backed widget replies require idle.
    Wait Until Keyword Succeeds    30s    0.5s    Tool Operation Should Be Finished    ${operation}

Tool Operation Should Be Finished
    [Arguments]    ${operation}
    ${state} =    Tool State
    Should Be Equal    ${state}[operation]    ${operation}
    Should Be True    $state['done'] and not $state['cancelled'] and $state['error'] is None    ${state}

Run Tool Code In A New Cell
    [Arguments]    ${code}    ${screen}=${EMPTY}
    ${token} =    Evaluate    'TOOLSCELLx' + secrets.token_hex(5)    secrets
    Run IPyElk Code In A New Cell    ${code}; print('${token}')    screen=${screen}
    # Idle may still describe the preceding cell. Verify this cell's own output
    # before sending another request, and expose its Python errors immediately.
    Wait For Condition
    ...    return (()=>{const token='${token}',cells=window.jupyterapp.shell.currentWidget.content.widgets;const cell=cells.find(c=>c.model.sharedModel.getSource().includes(token));const outputs=cell?.model.toJSON().outputs||[],text=o=>Array.isArray(o.text)?o.text.join(''):o.text||'';return outputs.some(o=>o.output_type==='error'||o.output_type==='stream'&&text(o).includes(token));})();
    ...    timeout=30s
    Page Should Not Contain Contain Standard Errors
    ${cell result} =    Execute Javascript
    ...    const token=arguments[0],cell=window.jupyterapp.shell.currentWidget.content.widgets.find(c=>c.model.sharedModel.getSource().includes(token));const outputs=cell.model.toJSON().outputs,text=o=>Array.isArray(o.text)?o.text.join(''):o.text||'';return {completed:outputs.some(o=>o.output_type==='stream'&&text(o).includes(token)),errors:outputs.filter(o=>o.output_type==='error').map(o=>o.ename+': '+o.evalue)};
    ...    ARGUMENTS
    ...    ${token}
    Should Be Empty    ${cell result}[errors]    tool cell failed: ${cell result}
    Should Be True    ${cell result}[completed]    the requested tool cell did not emit its completion token

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
    ...    const transport=window.toolProbeTransport;if(transport.failure)throw Error(transport.failure);const token=arguments[0],q={done:false,stdout:'',stderr:'',reply:null,error:null,answer:null};transport.answers[token]=q;
    ...    const fail=error=>{q.error=String(error);transport.failure=q.error;q.done=true;};
    ...    try{const f=window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.requestExecute({code:"_tools.report('"+token+"')"});
    ...    f.onIOPub=m=>{if(m.header.msg_type==='stream'){q[m.content.name==='stderr'?'stderr':'stdout']+=m.content.text;if(m.content.name==='stderr')fail(q.stderr);}else if(m.header.msg_type==='error'){fail(m.content.ename+': '+m.content.evalue);}};
    ...    f.done.then(reply=>{q.reply=reply.content;if(q.error||q.stderr||q.reply.status!=='ok'){fail(q.error||q.stderr||JSON.stringify(q.reply));return;}const line=q.stdout.split('\\n').find(line=>line.startsWith(token+' '));if(!line){fail('completed query has no token: '+q.stdout);return;}try{q.answer=JSON.parse(line.slice(token.length+1));q.done=true;}catch(error){fail('invalid query JSON: '+error);}}).catch(fail);
    ...    }catch(error){fail(error);}
    ...    ARGUMENTS
    ...    ${token}
    Wait For Condition    return window.toolProbeTransport.answers['${token}']?.done    timeout=30s
    ${query} =    Execute Javascript
    ...    const answers=window.toolProbeTransport.answers,answer=answers[arguments[0]];delete answers[arguments[0]];return answer;
    ...    ARGUMENTS
    ...    ${token}
    Should Be Equal    ${query}[error]    ${None}    tool query failed: ${query}
    ${state} =    Set Variable    ${query}[answer]
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
    Run Tool Code In A New Cell    _tools.assert_export(); print('TOOLS-EXPORT-PASS')    screen=${EMPTY}
    Wait Until Page Contains    TOOLS-EXPORT-PASS    timeout=2s
    Page Should Not Contain Contain Standard Errors
