*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}              ${SCREENS ROOT}${/}examples${/}04_Interactive
${CONVERGE TIMEOUT}     30s
${XP SLIDER}            //div[contains(@class, "widget-slider")][.//label[text()="{}"]]
${JS DOM CENSUS}
...                     const n = {};
...                     for (const el of document.querySelectorAll(".elknode, .elkedge, .elklabel, .elkport")) {
...                     const kind = [...el.classList].find((c) => /^elk(node|edge|label|port)$/.test(c));
...                     const key = kind + (el.closest(".sprotty-hidden") ? ":hidden" : "");
...                     n[key] = (n[key] || 0) + 1; }
...                     return JSON.stringify(n);
# one line, and no ``+``: Press Keys reads it as a chord
${COUNT CELL}
...                     from ipyelk.elements import index as _i, Node as _N, Edge as _E, Label as _L, Port as _P;
...                     _c95 = globals().get("_c95") or (lambda n: (elk.observe(n.append, "source"), n)[1])([]);
...                     _w = box.children[0].children[0].children; _x = list(_i.iter_elements(elk.source.value));
...                     print("ELK95", _w[0].value, _w[3].value, sum(isinstance(e, _N) for e in _x) - 1,
...                     sum(isinstance(e, _E) for e in _x), sum(isinstance(e, _L) for e in _x),
...                     sum(isinstance(e, _P) for e in _x), len(_c95),
...                     sum(isinstance(e, _N) for e in _i.iter_elements(elk.view.source.value)) - 1)


*** Test Cases ***
04_Interactive
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    # not worth counting anything, as is basically non-deterministic

04_Interactive Converges After Slider Bursts
    [Documentation]    Bursts of slider changes each replace ``elk.source``. Once a
    ...    burst stops, ``elk.source`` must hold the last requested graph and the
    ...    diagram must draw it, without touching the collapse toggle, once the
    ...    only way out of a hang (gh-95).
    [Tags]    gh:95
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    Diagram Should Converge    00
    Burst Sliders And Converge    01    ARROW_RIGHT    8
    Burst Sliders And Converge    02    ARROW_LEFT    15
    Burst Sliders And Converge    03    ARROW_RIGHT    10
    Burst Sliders And Converge    04    ARROW_LEFT    6
    Burst Sliders And Converge    05    ARROW_RIGHT    8


*** Keywords ***
Burst Sliders And Converge
    [Documentation]    Alternate single steps of ``number_of_nodes`` and ``seed``,
    ...    each a committed change and so a fresh ``make_graph``, as fast as
    ...    WebDriver allows, then wait for the diagram.
    [Arguments]    ${round}    ${key}    ${steps}
    FOR    ${i}    IN RANGE    ${steps}
        Press Slider Keys    number_of_nodes    ${key}
        Press Slider Keys    seed    ARROW_RIGHT
    END
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
    [Documentation]    Wait until ``elk.source`` holds the last request and, with the
    ...    diagram scrolled into view, the DOM draws it. Log the seconds since
    ...    ``${since}``, e.g. the end of a burst.
    [Arguments]    ${round}    ${since}=${None}
    ${since} =    Evaluate    $since or time.time()    time
    ${nodes ui} =    Get Slider Readout    number_of_nodes
    ${seed ui} =    Get Slider Readout    seed
    ${ok}    ${state} =    Run Keyword And Ignore Error
    ...    Wait Until Keyword Succeeds    ${CONVERGE TIMEOUT}    0.5s
    ...    Kernel Should Hold The Request    ${nodes ui}    ${seed ui}    ${round}
    Execute Javascript    document.querySelector("${CSS ELK VIEW}").scrollIntoView({block: "center"})
    IF    "${ok}" == "PASS"
        ${ok}    ${err} =    Run Keyword And Ignore Error
        ...    Wait Until Keyword Succeeds    ${CONVERGE TIMEOUT}    0.25s
        ...    Elk Counts Should Really Be    &{state.counts}    screen=${round}-1-counting.png
    ELSE
        ${err} =    Set Variable    ${state}
    END
    ${took} =    Evaluate    round(time.time() - ${since}, 2)    time
    Log    round ${round}: ${nodes ui}/${seed ui} ${ok} after ${took}s    console=True
    Capture Page Screenshot    ${round}-2-${ok.lower()}.png
    IF    "${ok}" == "FAIL"
        ${dom} =    Execute Javascript    ${JS DOM CENSUS}
        Fail    round ${round}: no convergence within ${CONVERGE TIMEOUT}, drawn ${dom}: ${err}
    END

Kernel Should Hold The Request
    [Documentation]    The kernel's sliders must match the browser's, and
    ...    ``elk.source`` must hold that graph.
    [Arguments]    ${nodes ui}    ${seed ui}    ${round}
    ${state} =    Get Kernel State
    Log    round ${round}: kernel ${state}    console=True
    Should Be Equal As Strings    ${state.sliders}    ${nodes ui}/${seed ui}
    ...    kernel sliders lag the browser    values=${TRUE}
    Should Be Equal As Strings    ${state.counts.nodes}    ${nodes ui}
    ...    elk.source is not the last requested graph    values=${TRUE}
    RETURN    ${state}

Get Kernel State
    ${token} =    Evaluate    "ELK95x%s" % secrets.token_hex(4)    secrets
    Run IPyElk Code In A New Cell    ${COUNT CELL.replace("ELK95", "${token}")}
    ${xp} =    Set Variable    xpath://*[contains(@class, "jp-OutputArea-output")][contains(., "${token} ")]
    Wait Until Page Contains Element    ${xp}    timeout=30s
    ${out} =    Get Text    ${xp}
    ${found} =    Get Regexp Matches    ${out}    ${token} (\\d+) (\\d+) (\\d+) (\\d+) (\\d+) (\\d+) (\\d+) (\\d+)
    ...    1    2    3    4    5    6    7    8
    Should Not Be Empty    ${found}
    ${f} =    Set Variable    ${found}[0]
    &{counts} =    Create Dictionary    nodes=${f}[2]    edges=${f}[3]    labels=${f}[4]    ports=${f}[5]
    &{state} =    Create Dictionary    sliders=${f}[0]/${f}[1]    sources=${f}[6]    view nodes=${f}[7]
    ...    counts=${counts}
    RETURN    ${state}
