*** Variables ***
${INTRODUCTION}    00_Introduction
${LINKING}        01_Linking
${TRANSFORMER}    02_Transformer
${APP}            03_App
${INTERACTIVE}    04_Interactive
${EXPORTER}       05_SVG_Exporter
${APP EXPORTER}    06_SVG_App_Exporter
${SIM PLUMBING}    07_Simulation
${SIM APP}        08_Simulation_App
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
${SIMPLE CUSTOM CLASSES}    .example-data-node-class-from-simple    .example-data-edge-class-from-simple
#
# from flat_graph.json
#
${FLAT NODE COUNT}    ${3}
${FLAT EDGE COUNT}    ${3}
${FLAT LABEL COUNT}    ${FLAT NODE COUNT}
${FLAT PORT COUNT}    ${1}
${FLAT CUSTOM CLASSES}    .example-data-node-class-from-flat    .example-data-edge-class-from-flat
#
# from hier_graph.json
#
${HIER NODE COUNT}    ${4}
${HIER EDGE COUNT}    ${5}
${HIER LABEL COUNT}    ${HIER NODE COUNT}
${HIER TREE CUSTOM CLASSES}    .example-data-node-class-from-tree
#
# from hier_ports.json
#
${HIER PORT COUNT}    ${8}
${HIER PORT CUSTOM CLASSES}    .example-data-node-class-from-ports    .example-data-edge-class-from-ports
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
...               ports=${FLAT PORT COUNT}
&{FLAT AND HIER COUNTS}
...               nodes=${FLAT NODE COUNT.__add__(${HIER NODE COUNT})}
...               edges=${FLAT EDGE COUNT.__add__(${HIER EDGE COUNT})}
...               labels=${FLAT LABEL COUNT.__add__(${HIER LABEL COUNT})}
...               ports=${FLAT PORT COUNT.__add__(${HIER PORT COUNT})}
