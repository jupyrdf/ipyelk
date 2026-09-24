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
    Fit Cervidae Tree
    Click Cervidae Junction    Odocoileini
    Elk Counts Should Be    nodes=${76}    edges=${75}    labels=${56}    ports=${152}
    Page Should Contain Element    css:[id$="Odocoileini.__toggle"] circle
    Click Cervidae Junction    Odocoileini
    Elk Counts Should Be    nodes=${109}    edges=${108}    labels=${82}    ports=${218}
    Capture Page Screenshot    11-cervidae-tree.png


*** Keywords ***
Fit Cervidae Tree
    # The notebook helper scrolls back to the first cell. SVG panning is not
    # document scrolling: fit the graph before trying to click a distant node.
    # Fit zooms to the selection, and a toggle click selects its taxon, so fit
    # once, before the first toggle click.
    ${app} =    Get WebElement    css:.jp-ElkApp
    Execute Javascript    arguments[0].scrollIntoView({block: "center"})    ARGUMENTS    ${app}
    Mouse Over    ${app}
    Click Element    ${app}
    ${fit} =    Set Variable    css:.jp-ElkToolbar button[title="Fit the tree in the viewport"]
    Wait Until Element Is Visible    ${fit}
    Click Element    ${fit}
    Wait Until Keyword Succeeds    10x    0.5s    Cervidae Toggles Should Be In View

Cervidae Toggles Should Be In View
    ${shown} =    Execute Javascript
    ...    const svg = document.querySelector('.jp-ElkView svg.sprotty-graph'), view = svg.getBoundingClientRect();
    ...    return [...svg.querySelectorAll('.taxonomy-toggle')].every((toggle) => {
    ...    const r = toggle.getBoundingClientRect();
    ...    return r.left >= view.left && r.top >= view.top && r.right <= view.right && r.bottom <= view.bottom;
    ...    });
    Should Be True    ${shown}

Click Cervidae Junction
    [Arguments]    ${parent}
    # Fit and re-layout move the SVG camera; retry until the toggle is clicked.
    Wait Until Keyword Succeeds    10x    0.5s
    ...    Click Cervidae Toggle    css:.jp-ElkView [id$="${parent}.__toggle"] circle

Click Cervidae Toggle
    [Arguments]    ${locator}
    ${el} =    Get WebElement    ${locator}
    Execute Javascript    arguments[0].scrollIntoView({block: "center", inline: "center"})    ARGUMENTS    ${el}
    # The -/+ glyph covers the circle's centre, so `Click Element` reports the
    # circle as obscured. Wait until the Fit camera stops and the circle or its
    # glyph is on top at the centre, then click there with the pointer.
    ${ready} =    Execute Async Javascript
    ...    const [el, done] = arguments, box = () => JSON.stringify(el.getBoundingClientRect()), before = box();
    ...    setTimeout(() => {
    ...    const r = el.getBoundingClientRect();
    ...    const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    ...    done(box() === before && el.parentNode.contains(hit));
    ...    }, 300);
    ...    ARGUMENTS    ${el}
    Should Be True    ${ready}
    Click Element At Coordinates    ${el}    0    0
