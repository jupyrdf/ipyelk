
import {
    DOMWidgetView,
} from '@jupyter-widgets/base';

import { injectable } from "inversify";
import {
    ActionHandlerRegistry, SelectAction, HoverFeedbackAction, CenterAction, CenterCommand,
    // IActionHandler, IActionHandlerInitializer,
    Action, LocalModelSource, BringToFrontAction, SelectCommand, ICommandStack
    //  SModelElementSchema,
    //  FluentIterable
} from "sprotty";
import { ElkGraphJsonToSprotty } from './json/elkgraph-to-sprotty';


@injectable()
export class JLModelSource extends LocalModelSource {
    view: any; //DOMWidgetView
    commandStack: ICommandStack;

    initialize(registry: ActionHandlerRegistry): void {
        super.initialize(registry);

        // Register this model source
        registry.register(SelectAction.KIND, this)
        registry.register(HoverFeedbackAction.KIND, this)
    }

    updateLayout(layout){
        let sGraph = new ElkGraphJsonToSprotty().transform(layout);
        this.updateModel(sGraph);        
    }

    handle(action: Action) {
        switch (action.kind) {
            case SelectAction.KIND:
                this.handleSelect(action as SelectAction)
                this.view._handle_click(action)
                break;
            case HoverFeedbackAction.KIND:
                this.handleHover(action as HoverFeedbackAction)
                break;
            case BringToFrontAction.KIND:
                break;
            default:
                super.handle(action);
                break;
        }
    }
    
    setup(view: DOMWidgetView, commandStack: ICommandStack) {
        this.view = view;
        this.commandStack = commandStack;
    }

    protected handleHover(action: HoverFeedbackAction) {
        let id: string;
        if (action.mouseIsOver) {
            id = action.mouseoverElement;
        } else {
            id = null
        }
        this.view.model.set("hovered", id);
        this.view.touch()
    }

    async getSelected() {
        let ids = []
        let selected = await this.getSelection()
        selected.forEach((node, i) => {
            ids.push(node.id)
        });
        return ids;
    }

    async setSelected(selectedIDs: string[], deselectedIDs: string[]) {
        let action: SelectAction = new SelectAction(selectedIDs, deselectedIDs);
        this.commandStack.execute(new SelectCommand(action))
    }

    protected handleSelect(action: SelectAction) {
        this.getSelected().then(ids => {
            this.view.model.set("selected", ids);
            this.view.touch();
        });

    }

    center(elementIds:string[]=[]){
        let action: CenterAction = new CenterAction(elementIds)
        this.commandStack.execute(new CenterCommand(action))
    }

    handleMessage(content, buffers){
        console.log('custom msg', content, buffers);
        switch (content.action){
            case "center": {
                let elementIds:string[]
                if (content.hasOwnProperty('model_id')){
                    if (!Array.isArray(content.model_id)){
                        elementIds = [content.model_id]
                    } else {
                        elementIds = content.model_id
                    }
                } else {
                    elementIds = []
                }
                this.center(elementIds)
                
            }
        }
    }

}
