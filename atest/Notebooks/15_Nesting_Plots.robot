*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}${NESTING PLOTS}
${JS CLICK}
...             if (!arguments[0].isConnected) throw new Error("Click target is detached");
...             for (const type of ["mousedown", "mouseup", "click"]) {
...             arguments[0].dispatchEvent(new MouseEvent(type, {bubbles: true, button: 0}));
...             }


*** Test Cases ***
15_Nesting_Plots
    Example Should Restart-and-Run-All    ${NESTING PLOTS}
    Scroll To Last Cell
    BQPlot Figure Count Should Be    ${0}
    ${sel} =    Set Variable    css:[title="expand and center"]
    # the button is disabled while the toggle runs: wait for disabled, then
    # enabled, or the wait can return before the kernel has disabled it
    Click Element    ${sel}
    Wait Until Element Is Not Enabled    ${sel}    timeout=10s
    Wait Until Element Is Enabled    ${sel}    timeout=30s
    Capture Page Screenshot    11-expanded.png
    BQPlot Figure Count Should Be    ${4}
    Click In A Widget Node Should Not Select It
    Click Element    ${sel}
    Wait Until Element Is Not Enabled    ${sel}    timeout=10s
    Wait Until Element Is Enabled    ${sel}    timeout=30s
    Capture Page Screenshot    12-collapsed.png
    BQPlot Figure Count Should Be    ${0}


*** Keywords ***
Click In A Widget Node Should Not Select It
    [Documentation]    A click inside the widget that a widget node shows, here on
    ...    a tick label of a bqplot figure, belongs to the widget: the selection
    ...    does not change. It used to select the widget node instead of the nodes
    ...    that the expand selected, as the tick label is not the widget's own
    ...    element. The events are dispatched on the tick label itself, so a
    ...    pointer cannot land on a brush or on the figure instead.
    ${tick} =    Set Variable
    ...    xpath:(//div[contains(@class,"elkcontainer")]//*[contains(@class,"bqplot")]//*[local-name()="g"][contains(@class,"tick")]/*[local-name()="text"])[1]
    Wait Until Page Contains Element    ${tick}    timeout=30s
    ${container} =    Get WebElement    ${tick}/ancestor::div[contains(@class,"elkcontainer")][1]
    ${id} =    Get Element Attribute    ${container}    id
    Should Not Be Empty    ${id}    the widget node's container has no DOM id
    ${app} =    Set Variable    ${tick}/ancestor::div[contains(@class,"jp-ElkApp")][1]
    ${selected} =    Set Variable
    ...    ${app}//*[contains(@class,"elknode")][contains(concat(" ", @class, " "), " selected ")]
    # the widget node's own shape takes the `selected` class: without it, nothing is tested
    ${shape} =    Set Variable    ${app}//*[local-name()="g"][@id="${id}"]/*[contains(@class,"elknode")]
    Wait Until Page Contains Element    ${shape}    timeout=30s
    # `expand_and_center` selected the four top-level nodes
    Wait Until Keyword Succeeds    10x    0.5s    Element Count Should Be    ${selected}    ${4}
    ${el} =    Get WebElement    ${tick}
    Execute Javascript    ${JS CLICK}    ARGUMENTS    ${el}
    # a selection would render within a frame or two; give it time
    Sleep    1s
    Capture Page Screenshot    11b-clicked-widget-node.png
    Page Should Not Contain Element    ${shape}\[contains(concat(" ", @class, " "), " selected ")]
    Element Count Should Be    ${selected}    ${4}
    # Positive control: the same event dispatch selects the ordinary node shape.
    ${shape el} =    Get WebElement    ${shape}
    Execute Javascript    ${JS CLICK}    ARGUMENTS    ${shape el}
    Wait Until Page Contains Element
    ...    ${shape}\[contains(concat(" ", @class, " "), " selected ")]
    ...    timeout=10s
    Element Count Should Be    ${selected}    ${1}

Element Count Should Be
    [Arguments]    ${locator}    ${expected}
    ${count} =    SeleniumLibrary.Get Element Count    ${locator}
    Should Be Equal As Integers    ${count}    ${expected}    ${locator} matched ${count}
