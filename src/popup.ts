import { injectable } from "inversify";
import {
    SModelElementSchema, SModelRootSchema, RequestPopupModelAction, PreRenderedElementSchema, IPopupModelProvider
} from "sprotty";

@injectable()
export class PopupModelProvider implements IPopupModelProvider {

    getPopupModel(request: RequestPopupModelAction, element?: SModelElementSchema): SModelRootSchema | undefined {
        if (element !== undefined && element.type === 'node:class') {
            return {
                type: 'html',
                id: 'popup',
                children: [
                    <PreRenderedElementSchema> {
                        type: 'pre-rendered',
                        id: 'popup-title',
                        code: `<div class="sprotty-popup-title">Class ${element.id === 'node0' ? 'Foo' : 'Bar'}</div>`
                    },
                    <PreRenderedElementSchema> {
                        type: 'pre-rendered',
                        id: 'popup-body',
                        code: '<div class="sprotty-popup-body">But I must explain to you how all this mistaken idea of denouncing pleasure and praising pain was born and I will give you a complete account of the system, and expound the actual teachings of the great explorer of the truth, the master-builder of human happiness.</div>'
                    }
                ]
            };
        }
        return undefined;
    }

}