*** Settings ***
Library           OperatingSystem
Library           Process
Library           String
Resource          Lab.robot
Resource          Browser.robot
Resource          Meta.robot
Resource          ../variables/Server.robot
Library           ../../_libraries/Ports.py

*** Keywords ***
Setup Server and Browser
    ${port} =    Get Unused Port
    Run Keyword and Ignore Error    Tag for Pabot
    Set Global Variable    ${PORT}    ${port}
    Set Global Variable    ${URL}    http://localhost:${PORT}${URL PREFIX}
    ${accel} =    Evaluate    "COMMAND" if "${OS}" == "Darwin" else "CTRL"
    Set Global Variable    ${ACCEL}    ${accel}
    ${token} =    Generate Random String
    Set Global Variable    ${TOKEN}    ${token}
    ${home} =    Set Variable    ${OUTPUT DIR}${/}home
    ${root} =    Normalize Path    ${OUTPUT DIR}${/}..${/}..${/}..
    Create Directory    ${home}
    Create Notebok Server Config    ${home}
    Initialize User Settings
    ${cmd} =    Create Lab Launch Command    ${root}
    Set Screenshot Directory    ${SCREENS ROOT}
    Set Global Variable    ${NEXT LAB}    ${NEXT LAB.__add__(1)}
    Set Global Variable    ${LAB LOG}    ${OUTPUT DIR}${/}lab-${PABOT ID}-${NEXT LAB}.log
    Set Global Variable    ${PREVIOUS LAB LOG LENGTH}    0
    ${server} =    Start Process    ${cmd}    shell=yes    env:HOME=${home}    cwd=${home}    stdout=${LAB LOG}
    ...    stderr=STDOUT
    Set Global Variable    ${SERVER}    ${server}
    Wait For Jupyter Server To Be Ready
    Open JupyterLab
    ${script} =    Get Element Attribute    id:jupyter-config-data    innerHTML
    ${config} =    Evaluate    __import__("json").loads("""${script}""")
    Set Global Variable    ${PAGE CONFIG}    ${config}
    Set Global Variable    ${LAB VERSION}    ${config["appVersion"]}

Create Lab Launch Command
    [Arguments]    ${root}
    [Documentation]    Create a JupyterLab CLI shell string, escaping for traitlets
    ${WORKSPACES DIR} =    Set Variable    ${OUTPUT DIR}${/}workspaces
    ${app args} =    Set Variable    --no-browser --debug --NotebookApp.base_url\='${URL PREFIX}' --port\=${PORT} --NotebookApp.token\='${TOKEN}'
    ${path args} =    Set Variable    --LabApp.user_settings_dir\='${SETTINGS DIR.replace('\\', '\\\\')}' --LabApp.workspaces_dir\='${WORKSPACES DIR.replace('\\', '\\\\')}'
    ${cmd} =    Set Variable
    ...    ${JUPYTERLAB_EXE} ${app args} ${path args}
    [Return]    ${cmd}

Create Notebok Server Config
    [Arguments]    ${home}
    [Documentation]    Copies in notebook server config file to disables npm/build checks
    Copy File    ${FIXTURES}${/}${NBSERVER CONF}    ${home}${/}${NBSERVER CONF}

Initialize User Settings
    Set Suite Variable    ${SETTINGS DIR}    ${OUTPUT DIR}${/}user-settings    children=${True}
    Create File    ${SETTINGS DIR}${/}@jupyterlab${/}codemirror-extension${/}commands.jupyterlab-settings
    ...    {"styleActiveLine": true}
    Create File    ${SETTINGS DIR}${/}@jupyterlab${/}extensionmanager-extension${/}plugin.jupyterlab-settings
    ...    {"enabled": false}

Tear Down Everything
    Close All Browsers
    Evaluate    __import__("urllib.request").request.urlopen("${URL}api/shutdown?token=${TOKEN}", data=[])
    Wait For Process    ${SERVER}    timeout=30s
    Terminate All Processes
    Terminate All Processes    kill=${True}

Wait For Jupyter Server To Be Ready
    Wait Until Keyword Succeeds    5x    5s
    ...    Evaluate    __import__("urllib.request").request.urlopen("${URL}")
