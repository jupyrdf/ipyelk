import { injectable } from "inversify";
import {
       CenterAction, 
        LocalModelSource,
} from "sprotty";
import { ElkGraphJsonToSprotty } from './json/elkgraph-to-sprotty';



@injectable()
export class JLModelSource extends LocalModelSource {
    async updateLayout(layout){
        let sGraph = new ElkGraphJsonToSprotty().transform(layout);
        await this.updateModel(sGraph);
        // TODO this promise resolves before ModelViewer rendering is done. need to hook into postprocessing
    }
    
    async getSelected() {
        let ids = []
        let selected = await this.getSelection()
        selected.forEach((node, i) => {
            ids.push(node.id)
        });
        return ids;
    }

    center(elementIds:string[]=[]){
        let action: CenterAction = new CenterAction(elementIds);
        this.actionDispatcher.dispatch(action);
    }
}
