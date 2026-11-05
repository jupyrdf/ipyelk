*** Settings ***
Resource    Browser.robot
Resource    Lab.robot
Resource    IPyElk.robot
Resource    ../variables/Server.robot


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}tools
${TOOL A}       xpath:(//div[contains(@class,"tools-probe")]//div[contains(@class,"jp-ElkView")])[1]//*[substring(@id,string-length(@id)-7)='_tools-a']
${JS VIEWS}     return [...document.querySelectorAll('.tools-probe .jp-ElkView')].map(v => v.querySelector('svg > g').getAttribute('transform'));


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
    [Arguments]    ${reset}=${FALSE}
    # Query without scrolling or moving the pointer off the diagram under test.
    ${token} =    Evaluate    'TOOLSx' + secrets.token_hex(5)    secrets
    Execute Javascript
    ...    const transport=window.toolProbeTransport;if(transport.failure)throw Error(transport.failure);const token=arguments[0],reset=arguments[1],q={done:false,stdout:'',stderr:'',reply:null,error:null,answer:null};transport.answers[token]=q;
    ...    const fail=error=>{q.error=String(error);transport.failure=q.error;q.done=true;};
    ...    try{const f=window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.requestExecute({code:(reset?"_tools.reset_events(); ":"")+"_tools.report('"+token+"')"});
    ...    f.onIOPub=m=>{if(m.header.msg_type==='stream'){q[m.content.name==='stderr'?'stderr':'stdout']+=m.content.text;if(m.content.name==='stderr')fail(q.stderr);}else if(m.header.msg_type==='error'){fail(m.content.ename+': '+m.content.evalue);}};
    ...    f.done.then(reply=>{q.reply=reply.content;if(q.error||q.stderr||q.reply.status!=='ok'){fail(q.error||q.stderr||JSON.stringify(q.reply));return;}const line=q.stdout.split('\\n').find(line=>line.startsWith(token+' '));if(!line){fail('completed query has no token: '+q.stdout);return;}try{q.answer=JSON.parse(line.slice(token.length+1));q.done=true;}catch(error){fail('invalid query JSON: '+error);}}).catch(fail);
    ...    }catch(error){fail(error);}
    ...    ARGUMENTS
    ...    ${token}
    ...    ${reset}
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

Prepare Tool Viewport Gesture
    ${canvas} =    Get WebElement    css:.tools-probe .sprotty-root
    Execute Javascript    arguments[0].scrollIntoView({block:'center'})    ARGUMENTS    ${canvas}
    # Wait for both actual public canvas reports after visible preparation.
    # Arm without another UI cell, which would scroll the diagram away again.
    Wait Until Keyword Succeeds    30s    0.5s    Tool Canvas Reports Should Match DOM
    ${sizes} =    Tool Canvas Sizes
    ${before} =    Execute Javascript    ${JS VIEWS}
    ${reset} =    Tool State    reset=${TRUE}
    Should Be Empty    ${reset}[camera_changes]
    Should Be Empty    ${reset}[camera_updates]
    RETURN    ${before}    ${sizes}

Tool Canvas Sizes
    ${sizes} =    Execute Javascript
    ...    return [...document.querySelectorAll('.tools-probe svg.sprotty-graph')].map(svg=>{const r=svg.getBoundingClientRect();return [r.width,r.height];});
    RETURN    ${sizes}

Tool Canvas Reports Should Match DOM
    ${sizes} =    Tool Canvas Sizes
    ${state} =    Tool State
    ${reported} =    Evaluate    sorted($state['camera_sizes'].values())
    ${expected} =    Evaluate    sorted($sizes)
    Should Be Equal As Integers    ${reported.__len__()}    2
    Should Be Equal    ${reported}    ${expected}    both public canvas reports must match the visible SVG canvases

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
