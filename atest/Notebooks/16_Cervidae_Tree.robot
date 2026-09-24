*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}${CERVIDAE TREE}


*** Test Cases ***
Cervidae Tree Renders Its Frozen Snapshot
    Create Directory    ${OUTPUT DIR}${/}home${/}data
    Copy File    ${IPYELK_EXAMPLES}${/}data${/}cervidae-tree.zip    ${OUTPUT DIR}${/}home${/}data${/}cervidae-tree.zip
    Example Should Restart-and-Run-All    ${CERVIDAE TREE}    timeout=600s
    Elk Counts Should Be    nodes=${109}    edges=${108}    labels=${82}    ports=${218}
    Page Should Contain Element    css:.cervidae-card
    Page Should Contain Element    css:.jp-ElkToolbar button
    Click Cervidae Junction    Odocoileini
    Elk Counts Should Be    nodes=${76}    edges=${75}    labels=${56}    ports=${152}
    Page Should Contain Element    css:[id$="Odocoileini.__toggle"] circle
    Click Cervidae Junction    Odocoileini
    Elk Counts Should Be    nodes=${109}    edges=${108}    labels=${82}    ports=${218}
    Capture Page Screenshot    11-cervidae-tree.png


*** Keywords ***
Click Cervidae Junction
    [Arguments]    ${parent}
    # The notebook helper scrolls back to the first cell. SVG panning is not
    # document scrolling: fit the graph before trying to click a distant node.
    ${app} =    Get WebElement    css:.jp-ElkApp
    Execute Javascript    arguments[0].scrollIntoView({block: "center"})    ARGUMENTS    ${app}
    Mouse Over    ${app}
    Click Element    ${app}
    ${fit} =    Set Variable    css:.jp-ElkToolbar button[title="Fit the tree in the viewport"]
    Wait Until Element Is Visible    ${fit}
    Click Element    ${fit}
    # Fit animates the SVG camera; retry native clicks until the circle is in view.
    Wait Until Keyword Succeeds    10x    0.5s
    ...    Click Element    css:.jp-ElkView [id$="${parent}.__toggle"] circle
