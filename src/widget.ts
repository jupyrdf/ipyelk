// Copyright (c) Dane Freeman.
// Distributed under the terms of the Modified BSD License.

import {
    DOMWidgetModel,
    DOMWidgetView,
    WidgetView,
    // ISerializers
} from '@jupyter-widgets/base';

import ELK from 'elkjs';
import { TYPES, SelectAction,
    // LocalModelSource, 
    // ActionHandlerRegistry, IActionHandler, SelectAction, SelectCommand 
} from 'sprotty';
import createContainer from './di-config';
import { ElkGraphJsonToSprotty } from './json/elkgraph-to-sprotty';
import {JLModelSource} from './diagram-server';

import _ from 'lodash';
(<any>window).ELK = ELK;


export class ELKModel extends DOMWidgetModel {
    defaults() {
        (<any>window).model = this;
        let defaults = {
            ...super.defaults(),
            value: {},
            diagram: {},
            _elk: new ELK({}),
        };
        this.setup();
        return defaults
    }

    setup() {
        this.on('change:value', this.value_changed, this);
    }

    async value_changed() {
        let value = this.get('value'),
            _elk = this.get('_elk');
        if (_elk) {
            let layout = await _elk.layout(value);
            this.set('diagram', layout);
        }
    }


}


export class ELKView extends DOMWidgetView {
    model: ELKModel;
    source: JLModelSource;
    container: any;
    private div_id:string;

    initialize(parameters: WidgetView.InitializeParameters){
        super.initialize(parameters);
        this.model.on('change:diagram', this.diagramLayout, this);
        this.model.on('change:selected', this.updateSelected, this);
        this.touch(); //to sync back the diagram state
        this.div_id  = 'sprotty-'+Math.random();
             
        // Create Sprotty viewer
        const sprottyContainer = createContainer(this.div_id, this);      
        this.container = sprottyContainer;  
        this.source = sprottyContainer.get<JLModelSource>(TYPES.ModelSource);

        (<any>window).view = this;   
    }

    /**
     * Dictionary of events and handlers
     */
    events(): {[e: string]: string} {
        return {'click': '_handle_click'};
    }

    /**
     * Handles when the button is clicked.
     */
    _handle_click(event: SelectAction) {
        // event.preventDefault();
        this.send({event: 'click', id:this.model.get('hovered')});
    }

    render() {
        this.$el[0].id = this.div_id;
        this.diagramLayout();
    }

    updateSelected(){
        let selected: string[] = this.model.get('selected');
        let old_selected:string[] = this.model.previous('selected');
        let exiting: string[] = _.difference(old_selected, selected);
        let entering: string[] = _.difference(selected, old_selected);
        this.source.setSelected(entering, exiting);
    }

    async diagramLayout() {
        let layout = this.model.get('diagram');
        this.touch();
        let sGraph = new ElkGraphJsonToSprotty().transform(layout);
        this.source.updateModel(sGraph);
    }
}
