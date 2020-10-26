*** Variables ***
${INTRODUCTION}    00_Introduction
${LINKING}        01_Linking
${TRANSFORMER}    02_Transformer
${APP}            03_App
${INTERACTIVE}    04_Interactive
${EXPORTER}       05_SVG_Exporter
${LABEL PLACEMENT}    100_node_label_placement
${TEXT SIZER}     101_text_sizer
${SIMPLE}         simple.json
${FLAT}           flat_graph.json
${HIER_PORTS}     hier_ports.json
${HIER_TREE}      hier_tree.json
@{SUPPORT}        ${IPYELK_EXAMPLES}${/}${SIMPLE}    ${IPYELK_EXAMPLES}${/}${FLAT}
...               ${IPYELK_EXAMPLES}${/}${HIER_PORTS}    ${IPYELK_EXAMPLES}${/}${HIER_TREE}
@{CLEANUP}        ${SIMPLE}    ${FLAT}    ${HIER_PORTS}    ${HIER_TREE}
