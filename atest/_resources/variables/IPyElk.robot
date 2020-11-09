*** Variables ***
${INTRODUCTION}    00_Introduction
${LINKING}        01_Linking
${TRANSFORMER}    02_Transformer
${APP}            03_App
${INTERACTIVE}    04_Interactive
${EXPORTER}       05_SVG_Exporter
${APP EXPORTER}    06_SVG_App_Exporter
${LABEL PLACEMENT}    100_node_label_placement
${TEXT SIZER}     101_text_sizer
${LAYOUT OPTIONS}    102_layout_options
${TX LAYOUT OPTIONS}    103_transformer_layout_options
${TX MULTI LABEL}    104_transformer_multi_label
${TX PORTS}       105_transformer_ports
${TX EDGES}       106_transformer_edges
${CSS ELK VIEW}    .jp-ElkView
${CSS SPROTTY GRAPH}    .sprotty-graph
${CSS ELK NODE}    .elknode
${CSS ELK EDGE}    .elkedge
${CSS ELK LABEL}    .elklabel
${CSS ELK PORT}    .elkport
#
# from simple.json
#
${SIMPLE NODE COUNT}    ${10}
${SIMPLE EDGE COUNT}    ${14}
${SIMPLE LABEL COUNT}    ${SIMPLE NODE COUNT}
#
# from flat_graph.json
#
${FLAT NODE COUNT}    ${3}
${FLAT EDGE COUNT}    ${3}
${FLAT LABEL COUNT}    ${FLAT NODE COUNT}
#
# from hier_graph.json
#
${HIER NODE COUNT}    ${4}
${HIER EDGE COUNT}    ${5}
${HIER LABEL COUNT}    ${HIER NODE COUNT}
#
# from hier_ports.json
#
${HIER PORT COUNT}    ${8}
#
# convenience roll-ups
#
&{SIMPLE COUNTS}
...               nodes=${SIMPLE NODE COUNT}
...               edges=${SIMPLE EDGE COUNT}
...               labels=${SIMPLE LABEL COUNT}
&{HIER COUNTS}
...               nodes=${HIER NODE COUNT}
...               edges=${HIER EDGE COUNT}
...               labels=${HIER LABEL COUNT}
...               ports=${HIER PORT COUNT}
&{FLAT COUNTS}
...               nodes=${FLAT NODE COUNT}
...               edges=${FLAT EDGE COUNT}
...               labels=${FLAT LABEL COUNT}
&{FLAT AND HIER COUNTS}
...               nodes=${FLAT NODE COUNT.__add__(${HIER NODE COUNT})}
...               edges=${FLAT EDGE COUNT.__add__(${HIER EDGE COUNT})}
...               labels=${FLAT LABEL COUNT.__add__(${HIER LABEL COUNT})}
...               ports=${HIER PORT COUNT}
