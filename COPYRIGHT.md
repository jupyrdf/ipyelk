# Copyright

Copyright (c) 2021 Dane Freeman. Distributed under the terms of the Modified BSD
License.

The package also contains code under the Eclipse Public License 1.0 and 2.0, listed
below, so its license expression is `BSD-3-Clause AND EPL-1.0 AND EPL-2.0`. The
permissive licenses of the other bundled packages ask only for their notices, which
`static/third-party-licenses.json` holds.

## Third-party Software

### Bundled JavaScript packages

The JupyterLab extension bundles third-party JavaScript packages. The extension's
`static/third-party-licenses.json` lists each bundled package with its version, license
and license text.

These bundled packages are available under the Eclipse Public License 2.0 or a GNU
General Public License. ipyelk distributes them under the Eclipse Public License 2.0, in
`third-party/epl-v20.html`:

- elkjs, https://github.com/kieler/elkjs: `EPL-2.0 OR GPL-3.0-or-later`
- sprotty and sprotty-protocol, https://github.com/eclipse-sprotty/sprotty:
  `EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0`

The other bundled packages are available under the MIT, ISC, Apache-2.0 or BSD-3-Clause
license.

### Source files derived from other works

Portions of this work are derived from other open source works.

#### Eclipse Public License 1.0

These files are available under the Eclipse Public License 1.0, in
`third-party/epl-v10.html`.

From https://github.com/kieler/elkjs, in `js/sprotty/json/elkgraph-to-sprotty.ts`:

> Copyright (c) 2017 Kiel University and others. All rights reserved. This program and
> the accompanying materials are made available under the terms of the Eclipse Public
> License v1.0 which accompanies this distribution, and is available at
> http://www.eclipse.org/legal/epl-v10.html

From https://github.com/eclipse/sprotty-layout, in `js/sprotty/di-config.ts`,
`js/sprotty/views/edge_views.tsx` and `js/sprotty/views/node_views.tsx`:

> Copyright (c) 2017 TypeFox GmbH (http://www.typefox.io) and others. All rights
> reserved. This program and the accompanying materials are made available under the
> terms of the Eclipse Public License v1.0 which accompanies this distribution, and is
> available at http://www.eclipse.org/legal/epl-v10.html

#### Eclipse Public License 2.0

These files are available under the Eclipse Public License 2.0, in
`third-party/epl-v20.html`. Each file's header gives its copyright and license.

- `js/sprotty/json/elkgraph-json.ts`, Copyright (c) 2019 TypeFox and others: `EPL-2.0`.
  The generated JSON schema `src/ipyelk/schema/elkschema.json` quotes the license
  headers of this file and of elkjs.
- `js/sprotty/update/update-model.ts`, Copyright (c) 2017-2020 TypeFox and others:
  `EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0`
- `js/tools/feedback/cursor-feedback.ts`,
  `js/tools/feedback/feedback-action-dispatcher.ts` and `js/tools/feedback/model.ts`,
  Copyright (c) 2019 EclipseSource and others:
  `EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0`
