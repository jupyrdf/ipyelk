*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Resource            ../_resources/variables/Server.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}              ${SCREENS ROOT}${/}examples${/}${NODE MENAGERIE}
${WIDGET NODE CLICK}    widget_node_click.py
${JS CLICK}
...                     for (const type of ["mousedown", "mouseup", "click"]) {
...                     arguments[0].dispatchEvent(new MouseEvent(type, {bubbles: true, button: 0}));
...                     }


*** Test Cases ***
12_Node_Menagerie
    Example Should Restart-and-Run-All    ${NODE MENAGERIE}
    Click In A Widget Node Should Not Select It


*** Keywords ***
Click In A Widget Node Should Not Select It
    [Documentation]    A click inside the widget that a widget node shows, here on
    ...    the icon of a button, belongs to the widget: the node stays unselected.
    ...    It used to be selected, as the icon is not the widget's own element. The
    ...    diagram is a new one in the last cell, as the example's own widget nodes
    ...    may be scrolled away or culled. The events go to the icon itself: a
    ...    pointer click at its centre could land on the button.
    Copy File    ${FIXTURES}${/}${WIDGET NODE CLICK}    ${OUTPUT DIR}${/}home${/}${WIDGET NODE CLICK}
    Run IPyElk Code In A New Cell    __import__("widget_node_click").app()
    ...    screen=11-widget-node.png
    ${app} =    Set Variable    xpath:(//div[contains(@class,"jp-ElkApp")])[last()]
    ${icon} =    Set Variable
    ...    ${app}//div[contains(@class,"elkcontainer")]//button[contains(@class,"jupyter-widgets")]//i
    Wait Until Page Contains Element    ${icon}    timeout=30s
    ${el} =    Get WebElement    ${icon}
    Execute Javascript    arguments[0].scrollIntoView({block: "center"})    ARGUMENTS    ${el}
    Execute Javascript    ${JS CLICK}    ARGUMENTS    ${el}
    # a selection would render within a frame or two; give it time
    Sleep    1s
    Capture Page Screenshot    12-clicked-widget-node.png
    Page Should Not Contain Element
    ...    ${app}//*[contains(@class,"elknode")][contains(concat(" ", @class, " "), " selected ")]
