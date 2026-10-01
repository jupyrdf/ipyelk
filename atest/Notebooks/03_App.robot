*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}03_App


*** Test Cases ***
03_App
    [Tags]    data:hier_tree.json    data:hier_ports.json    foo:bar
    Example Should Restart-and-Run-All    ${APP}
    Scroll To Cell    6
    Click Elk Tool    Center    1
    IF    ${TOTAL_COVERAGE}
        # n1 holds n2: selecting it makes the notebook show its control overlay.
        # Only where coverage is measured: on the `oldest` frontend (JupyterLab
        # 4.1.8, ipywidgets 8.0.1) selecting a node runs Firefox out of memory.
        Select Elk Node    n1
        Elk Control Overlay Should Show A Button
        Capture Page Screenshot    11-selected-n1.png
    END
    Scroll To Cell    9
    Click Elk Tool    Center    2
    Scroll To Cell    12
    Click Elk Tool    Center    3
    Scroll To Cell    15
    Click Elk Tool    Center    4
    Elk Counts Should Be    n=${4}    &{HIER COUNTS}
    Scroll To Cell    6
    Linked Elk Output Counts Should Be    &{HIER COUNTS}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}
