*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}${NODE MENAGERIE}


*** Test Cases ***
12_Node_Menagerie
    Example Should Restart-and-Run-All    ${NODE MENAGERIE}
    Click In A Widget Node Should Not Select It


*** Keywords ***
Click In A Widget Node Should Not Select It
    [Documentation]    A click inside the widget that a widget node shows, here on
    ...    the handle of a slider, belongs to the widget: the node stays unselected.
    ...    It used to be selected, as the handle is not the widget's own element.
    ${app} =    Set Variable    xpath:(//div[contains(@class,"jp-ElkApp")])[2]
    ${handle} =    Set Variable
    ...    ${app}//div[contains(@class,"elkcontainer")]//*[contains(@class,"noUi-handle")]
    Wait Until Page Contains Element    ${handle}    timeout=30s
    ${el} =    Get WebElement    ${handle}
    Execute Javascript    arguments[0].scrollIntoView({block: "center"})    ARGUMENTS    ${el}
    Click Element    ${el}
    # a selection would render within a frame or two; give it time
    Sleep    1s
    Capture Page Screenshot    11-clicked-widget-node.png
    Page Should Not Contain Element
    ...    ${app}//*[contains(@class,"elknode")][contains(concat(" ", @class, " "), " selected ")]
