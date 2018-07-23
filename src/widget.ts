// Copyright (c) Dane Freeman.
// Distributed under the terms of the Modified BSD License.

import {
    DOMWidgetModel,
    DOMWidgetView,
    ISerializers
} from '@jupyter-widgets/base';

import {EXTENSION_SPEC_VERSION} from './version';

import ELK from 'elkjs/lib/elk.bundled.js';
(<any>window).ELK = ELK;
export class ELKModel extends DOMWidgetModel {


    async value_changed() {
        let value = this.get('value');
        console.log('value:', value);
        (<any>window).value = value;
        if (this._elk) {
            let layout = await this._elk.layout(this.get('value'), {});
            this.set('layout', layout);
            (<any>window)._elk = this._elk;
        }
    }

    setup() {
        console.log('ELK3');
        this.on('change:value', this.value_changed, this);
    }

    defaults() {
        this.setup();
        (<any>window).model = this;

        return {
            ...super.defaults(),
            _model_name: ELKModel.model_name,
            _model_module: ELKModel.model_module,
            _model_module_version: ELKModel.model_module_version,
            _view_name: ELKModel.view_name,
            _view_module: ELKModel.view_module,
            _view_module_version: ELKModel.view_module_version,
            value: {},
            layout: {},
            _elk: new ELK({}),

        };
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
    render() {
        this.model.on('layout:value', this.layout_changed, this);
    }

    layout_changed() {
        console.log(this.model.get('layout'));
    }
}
