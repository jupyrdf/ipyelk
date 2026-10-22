*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Resource            ../_resources/variables/Server.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}              ${SCREENS ROOT}${/}examples${/}04_Interactive
# longer than a pipe's 30s wait for the browser: the macOS runners' kernel can be
# that far behind a burst, and a timed-out pipe may still recover
${CONVERGE TIMEOUT}     60s
${PROBE}                interactive_probe.py
${XP SLIDER}            //div[contains(@class, "widget-slider")][.//label[text()="{}"]]
# JupyterLab may scroll the view away to show a new cell, and stops updating
# outputs it has moved off-screen
${JS DRAWN EDGE IDS}
...                     document.querySelector("${CSS ELK VIEW}").scrollIntoView({block: "center"});
...                     return [...document.querySelectorAll("${CSS ELK VIEW} ${CSS ELK EDGE}")]
...                     .filter((el) => !el.closest(".sprotty-hidden"))
...                     .map((el) => el.id.slice(-36)).sort();
# tells a kernel that stopped running cells from a page that stopped drawing
${JS STALL}
...                     const cell = [...document.querySelectorAll(".jp-CodeCell")]
...                     .find((c) => c.querySelector(".jp-InputArea-editor")?.textContent.includes(arguments[0]));
...                     const prompt = cell?.querySelector(".jp-InputArea-prompt")?.textContent.trim();
...                     const pipe = document.querySelector(".elk-pipe-status")?.closest("pre");
...                     const status = pipe ? [...pipe.children].map((el) => el.textContent.trim()).filter(Boolean).join(" ") : "missing";
...                     return "prompt " + (prompt ?? "missing") + ", pipe " + JSON.stringify(status);


*** Test Cases ***
04_Interactive
    [Documentation]    Bursts of slider changes each replace ``elk.source``. Once a
    ...    burst stops, ``elk.source`` must hold the graph the sliders ask for, and
    ...    the diagram must draw that very graph (its edge ids are fresh uuids on
    ...    every load), without touching the collapse toggle, which was once the
    ...    only way out of a hang (gh-95). Bursts end on different sliders, so a
    ...    graph one step behind fails.
    ...
    ...    The race is intermittent and CI retries failed tests (``ATEST_RETRIES``),
    ...    so a first-attempt failure is the signal: ``scripts/atest.py`` keeps each
    ...    attempt's ``output.xml`` in ``build/reports/atest*/<os>_<attempt>/`` and
    ...    raises a GitHub warning for each test that failed before the last attempt
    ...    or was skipped on failure. ``ci.yml`` skips failures tagged ``gh:95`` on
    ...    some jobs; the tag is only set once the notebook has run, so the notebook
    ...    itself still gates everywhere.
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    Set Tags    gh:95
    Copy File    ${FIXTURES}${/}${PROBE}    ${OUTPUT DIR}${/}home${/}${PROBE}
    Run IPyElk Code In A New Cell    _k95 = __import__("interactive_probe").watch(box, elk)
    ...    screen=00-probe.png
    Set Test Variable    ${SOURCES SEEN}    ${0}
    Diagram Should Converge    00
    Burst Sliders And Converge    01    ARROW_RIGHT    7    number_of_nodes    ARROW_RIGHT
    Burst Sliders And Converge    02    ARROW_LEFT    14    number_of_nodes    ARROW_LEFT
    Burst Sliders And Converge    03    ARROW_RIGHT    11    percent_of_edges    ARROW_LEFT
    Burst Sliders And Converge    04    ARROW_LEFT    6    number_of_nodes    ARROW_LEFT
    Burst Sliders And Converge    05    ARROW_RIGHT    8


*** Keywords ***
Burst Sliders And Converge
    [Documentation]    Alternate single steps of ``number_of_nodes`` and ``seed``,
    ...    each a committed change and so a fresh ``make_graph``, as fast as
    ...    WebDriver allows, then one more ``@{last}`` step, then wait.
    [Arguments]    ${round}    ${key}    ${steps}    @{last}
    FOR    ${i}    IN RANGE    ${steps}
        Press Slider Keys    number_of_nodes    ${key}
        Press Slider Keys    seed    ARROW_RIGHT
    END
    IF    ${last}    Press Slider Keys    @{last}
    ${since} =    Evaluate    time.time()    time
    Capture Page Screenshot    ${round}-0-burst.png
    Diagram Should Converge    ${round}    ${since}

Press Slider Keys
    [Arguments]    ${description}    @{keys}
    ${handle} =    Get WebElement    xpath:${XP SLIDER.format("${description}")}//*[contains(@class, "noUi-handle")]
    Execute Javascript    arguments[0].focus()    ARGUMENTS    ${handle}
    Press Keys    None    @{keys}

Get Slider Readout
    [Arguments]    ${description}
    ${text} =    Get Text    xpath:${XP SLIDER.format("${description}")}//*[contains(@class, "widget-readout")]
    RETURN    ${text}

Diagram Should Converge
    [Documentation]    Wait until ``elk.source`` holds the graph the browser's sliders
    ...    ask for, then until the diagram draws it. Log when ``elk.source`` last
    ...    changed and when the drawing matched, in seconds since ``${since}``.
    [Arguments]    ${round}    ${since}=${None}
    ${since} =    Evaluate    $since or time.time()    time
    ${nodes} =    Get Slider Readout    number_of_nodes
    ${percent} =    Get Slider Readout    percent_of_edges
    ${seed} =    Get Slider Readout    seed
    ${asked} =    Set Variable    ${nodes}/${percent}/${seed}
    ${ok}    ${state} =    Run Keyword And Ignore Error
    ...    Wait Until Keyword Succeeds    ${CONVERGE TIMEOUT}    0.5s
    ...    Kernel Should Hold The Request    ${asked}
    IF    "${ok}" == "PASS"
        ${ok}    ${err} =    Run Keyword And Ignore Error
        ...    Wait Until Keyword Succeeds    ${CONVERGE TIMEOUT}    0.25s
        ...    Diagram Should Draw    ${state}[edges]
        ${held} =    Evaluate    round($state["changed_at"] - ${since}, 2)
        ${new} =    Evaluate    $state["changes"] - ${SOURCES SEEN}
        Set Test Variable    ${SOURCES SEEN}    ${state}[changes]
    ELSE
        ${err} =    Set Variable    ${state}
        ${held} =    Set Variable    ?
        ${new} =    Set Variable    ?
    END
    ${drawn} =    Evaluate    round(time.time() - ${since}, 2)    time
    Log    round ${round}: ${asked} ${ok}, ${new} new sources, last at ${held}s, drawn by ${drawn}s
    ...    console=True
    Capture Page Screenshot    ${round}-2-${ok.lower()}.png
    IF    "${ok}" == "FAIL"
        ${err} =    Evaluate    $err.split("The last error was: ")[-1]
        Fail    round ${round}: no convergence on ${asked} within ${CONVERGE TIMEOUT}: ${err}
    END
    IF    "${round}" != "00"
        Should Be True    ${new} > 0    burst ${round} never replaced elk.source
    END

Kernel Should Hold The Request
    [Arguments]    ${asked}
    ${state} =    Get Kernel State
    Should Be Equal    ${state}[sliders]    ${asked}    kernel sliders lag the browser    values=${TRUE}
    Should Be Equal    ${state}[held]    ${state}[requested]
    ...    elk.source is not the graph ${asked} asks for    values=${TRUE}
    RETURN    ${state}

Diagram Should Draw
    [Arguments]    ${edges}
    ${drawn} =    Execute Javascript    ${JS DRAWN EDGE IDS}
    ${missing} =    Evaluate    len(set($edges) - set($drawn))
    ${stale} =    Evaluate    len(set($drawn) - set($edges))
    Should Be True    $drawn == $edges
    ...    drawn ${drawn.__len__()} edges: ${missing} of elk.source's ${edges.__len__()} missing, ${stale} others

Get Kernel State
    ${token} =    Evaluate    "ELK95x%s" % secrets.token_hex(4)    secrets
    Run IPyElk Code In A New Cell    _k95("${token}")    screen=${EMPTY}
    ${xp} =    Set Variable    xpath://*[contains(@class, "jp-OutputArea-output")][contains(., "${token} ")]
    ${shown} =    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    ${xp}    timeout=${CONVERGE TIMEOUT}
    IF    not ${shown}
        ${stall} =    Execute Javascript    ${JS STALL}    ARGUMENTS    ${token}
        Fail    no answer to ${token} within ${CONVERGE TIMEOUT}: ${stall}
    END
    ${out} =    Get Text    ${xp}
    ${state} =    Evaluate    json.loads($out.split(" ", 1)[1])    json
    Log    ${state}
    RETURN    ${state}
