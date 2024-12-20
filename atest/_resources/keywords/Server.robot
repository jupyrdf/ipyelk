*** Settings ***
Library     OperatingSystem
Library     Process
Library     String
Resource    Lab.robot
Resource    Browser.robot
Resource    Coverage.robot
Resource    ../variables/Server.robot
Library     ../../_libraries/Ports.py
Library     json


*** Variables ***
${JUPYTERLAB_EXE}               jupyter-lab
${TOTAL_COVERAGE}               0
${CALLER_ID}                    0000
${PABOTQUEUEINDEX}              0
${PABOTEXECUTIONPOOLID}         0
${LAB MINOR WITH VIRTUAL}       2

# paths relative to home
${DOT_LOCAL_PATH}               .local
${ETC_PATH}                     ${DOT_LOCAL_PATH}${/}etc${/}jupyter
${SHARE_PATH}                   ${DOT_LOCAL_PATH}${/}share${/}jupyter
${KERNELS_PATH}                 ${SHARE_PATH}${/}kernels
${USER_SETTINGS_PATH}           ${ETC_PATH}${/}lab${/}user-settings


*** Keywords ***
Setup Server and Browser
    ${port} =    Get Unused Port
    Set Suite Variable    ${PORT}    ${port}    children=${TRUE}
    Set Suite Variable    ${URL}    http://localhost:${PORT}${URL PREFIX}    children=${TRUE}
    ${accel} =    Evaluate    "COMMAND" if "${OS}" == "Darwin" else "CTRL"
    Set Suite Variable    ${ACCEL}    ${accel}    children=${TRUE}
    ${token} =    Generate Random String
    Set Suite Variable    ${TOKEN}    ${token}    children=${TRUE}
    ${home} =    Set Variable    ${OUTPUT DIR}${/}home
    Create Directory    ${home}
    Create Directory    ${OUTPUT DIR}${/}logs
    Create Notebok Server Config    ${home}
    Initialize User Settings
    IF    "${TOTAL_COVERAGE}" == "1"    Initialize Coverage Kernel    ${home}
    ${cmd} =    Create Lab Launch Command
    Set Screenshot Directory    ${SCREENS ROOT}
    Set Suite Variable    ${NEXT LAB}    ${NEXT LAB.__add__(1)}    children=${TRUE}
    Set Suite Variable    ${LAB LOG}    ${OUTPUT DIR}${/}logs${/}lab-${NEXT LAB}.log    children=${TRUE}
    Set Suite Variable    ${PREVIOUS LAB LOG LENGTH}    0    children=${TRUE}
    ${server} =    Start Process    ${cmd}    shell=yes
    ...    env:HOME=${home}
    ...    env:JUPYTER_CONFIG_DIR=${home}${/}${ETC_PATH}
    ...    env:JUPYTER_PREFER_ENV_PATH=0
    ...    cwd=${home}
    ...    stdout=${LAB LOG}
    ...    stderr=STDOUT
    Set Suite Variable    ${SERVER}    ${server}    children=${TRUE}
    Wait For Jupyter Server To Be Ready
    Open JupyterLab
    ${script} =    Get Element Attribute    id:jupyter-config-data    innerHTML
    ${config} =    Evaluate    __import__("json").loads(r"""${script}""")
    Set Suite Variable    ${PAGE CONFIG}    ${config}    children=${TRUE}
    Set Suite Variable    ${LAB VERSION}    ${config["appVersion"]}    children=${TRUE}
    ${major} =    Convert To Integer    ${LAB VERSION.split(".")[0]}
    ${minor} =    Convert To Integer    ${LAB VERSION.split(".")[1]}
    Set Suite Variable    ${LAB VERSION MAJOR}    ${major}    children=${TRUE}
    Set Suite Variable    ${LAB VERSION MINOR}    ${minor}    children=${TRUE}
    ${virtual} =    Evaluate    ${minor} >= ${LAB MINOR WITH VIRTUAL}
    Set Suite Variable    ${LAB VIRTUAL SCROLLING}    ${virtual}    children=${TRUE}
    Set Tags    lab:${LAB VERSION}

Initialize Coverage Kernel
    [Documentation]    Copy and patch the env kernel to run under coverage.
    [Arguments]    ${home_dir}
    ${kernels_dir} =    Set Variable    ${home_dir}${/}${KERNELS_PATH}
    Create Directory    ${kernels_dir}
    ${spec_dir} =    Set Variable    ${kernels_dir}${/}python3
    Copy Directory    %{CONDA_PREFIX}${/}share${/}jupyter${/}kernels${/}python3    ${spec_dir}
    ${spec_path} =    Set Variable    ${spec_dir}${/}kernel.json
    ${spec_text} =    Get File    ${spec_path}
    ${spec_json} =    Loads    ${spec_text}
    ${cov_path} =    Set Variable    ${OUTPUT_DIR}${/}pycov
    Create Directory    ${cov_path}
    ${rest} =    Get Slice From List    ${spec_json["argv"]}    1
    ${argv} =    Create List
    ...    ${spec_json["argv"][0]}
    ...    -m
    ...    coverage
    ...    run
    ...    --parallel-mode
    ...    --branch
    ...    --source    ${ROOT}/src/ipyelk
    ...    --context    atest-${PABOTQUEUEINDEX}-${PABOTEXECUTIONPOOLID}-${CALLER_ID}
    ...    --concurrency    thread
    ...    --data-file    ${cov_path}${/}.coverage
    ...    @{rest}
    Set To Dictionary    ${spec_json}    argv=${argv}
    ${spec_text} =    Dumps    ${spec_json}    indent=${2}    sort_keys=${TRUE}
    Log    ${spec_text}
    Create File    ${spec_path}    ${spec_text}
    RETURN    ${spec_path}

Create Lab Launch Command
    [Documentation]    Create a JupyterLab CLI shell string, escaping for traitlets
    ${WORKSPACES DIR} =    Set Variable    ${OUTPUT DIR}${/}workspaces
    ${app args} =    Catenate
    ...    --no-browser
    ...    --debug
    ...    --port\=${PORT}
    ...    --ServerApp.base_url\='${URL PREFIX}'
    ...    --ServerApp.token\='${TOKEN}'
    ...    --ExtensionApp.open_browser\=False
    ...    --ServerApp.open_browser\=False
    ${path args} =    Catenate
    ...    --LabApp.user_settings_dir\='${SETTINGS DIR.replace('\\', '\\\\')}'
    ...    --LabApp.workspaces_dir\='${WORKSPACES DIR.replace('\\', '\\\\')}'
    IF    ${TOTAL_COVERAGE}
        ${path args} =    Catenate
        ...    ${path args}
        ...    --LabApp.extra_labextensions_path\='${ROOT.replace('\\', '\\\\')}${/}build${/}labextensions-cov'
    END
    ${cmd} =    Set Variable
    ...    jupyter-lab ${app args} ${path args}
    RETURN    ${cmd}

Create Notebok Server Config
    [Documentation]    Copies in notebook server config file to disables npm/build checks
    [Arguments]    ${home}
    Copy File    ${FIXTURES}${/}${NBSERVER CONF}    ${home}${/}${NBSERVER CONF}

Initialize User Settings
    [Documentation]    Configure the settings directory, and modify settings that make tests less reproducible
    Set Suite Variable    ${SETTINGS DIR}    ${OUTPUT DIR}${/}user-settings    children=${True}
    Create File
    ...    ${SETTINGS DIR}${/}@jupyterlab${/}codemirror-extension${/}commands.jupyterlab-settings
    ...    {"styleActiveLine": true}
    Create File
    ...    ${SETTINGS DIR}${/}@jupyterlab${/}extensionmanager-extension${/}plugin.jupyterlab-settings
    ...    {"enabled": false}
    Create File
    ...    ${SETTINGS DIR}${/}@jupyterlab${/}apputils-extension${/}palette.jupyterlab-settings
    ...    {"modal": false}
    Create File
    ...    ${SETTINGS DIR}${/}@jupyterlab${/}apputils-extension${/}notification.jupyterlab-settings
    ...    {"fetchNews": "false", "checkForUpdates": false}

Tear Down Everything
    Close All Browsers
    Evaluate    __import__("urllib.request").request.urlopen("${URL}api/shutdown?token=${TOKEN}", data=[])
    Wait For Process    ${SERVER}    timeout=30s
    Terminate All Processes
    Terminate All Processes    kill=${True}

Wait For Jupyter Server To Be Ready
    Wait Until Keyword Succeeds    5x    5s
    ...    Evaluate    __import__("urllib.request").request.urlopen("${URL}")
