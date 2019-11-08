// Copyright (c) Dane Freeman.
// Distributed under the terms of the Modified BSD License.

import {
    DOMWidgetModel,
    DOMWidgetView,
    ISerializers
} from '@jupyter-widgets/base';

import {EXTENSION_SPEC_VERSION} from './version';

import ELK from 'elkjs/lib/elk.bundled.js';
import * as d3 from 'd3';

(<any>window).ELK = ELK;
(<any>window).d3 = d3;

export class ELKModel extends DOMWidgetModel {


    async value_changed() {
        let value = this.get('value'),
            _elk = this.get('_elk');
        console.log('value:', value);
        (<any>window).value = value;
        if (_elk) {
            let layout = await _elk.layout(value, {});
            this.set('diagram', layout);
            (<any>window)._elk = this._elk;
        }
    }

    setup() {
        console.log('ELK3');
        this.on('change:value', this.value_changed, this);
    }

    defaults() {
        (<any>window).model = this;
        let defaults = {
            ...super.defaults(),
            _model_name: ELKModel.model_name,
            _model_module: ELKModel.model_module,
            _model_module_version: ELKModel.model_module_version,
            _view_name: ELKModel.view_name,
            _view_module: ELKModel.view_module,
            _view_module_version: ELKModel.view_module_version,
            value: {},
            diagram: {},
            _elk: new ELK({}),

        };
        this.setup();
        return defaults
    }

    static serializers: ISerializers = {
        ...DOMWidgetModel.serializers,
        // Add any extra serializers here
    }

    static model_name = 'ELKModel';
    static model_module = 'elk-widget';
    static model_module_version = EXTENSION_SPEC_VERSION;
    static view_name = 'ELKView';  // Set to null if no view
    static view_module = 'elk-widget';   // Set to null if no view
    static view_module_version = EXTENSION_SPEC_VERSION;
    private _elk: ELK;
}


export class ELKView extends DOMWidgetView {
    model: ELKModel;
    svg: any;

    render() {
        // var zoom = d3.behavior.zoom()
        //     .on("zoom", redraw);
        console.log('render ELKView', this);
        (<any>window).view = this;
        this.svg = d3.select(this.el)
            .append("svg")
            .attr("width", 100)
            .attr("height", 100)
            // .call(zoom)
            .append("g");

        this.model.on('change:diagram', this.diagramLayout, this);

    }

    async diagramLayout() {
        let diagram = this.model.get('diagram'),
            root = this.svg;

        console.log(this.model.get('diagram'));
        (<any>window).el = this.el;

        d3.select(this.el).append('text').html('1');
        var link = root.selectAll(".link")
              .data(graph.links)
              .enter()
              .append("path")
              .attr("class", "link")
              .attr("d", "M0 0");
          // we group nodes along with their ports
          var node = root.selectAll(".node")
              .data(graph.nodes)
              .enter()
              .append("g");

          node.append("rect")
              .attr("class", "node")
              .attr("width", 10)
              .attr("height", 10)
              .attr("x", 0)
              .attr("y", 0);
          node.append("title")
              .text(function(d) { return d.name; });
    }


}
