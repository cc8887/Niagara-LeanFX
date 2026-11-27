# 从 Fab 样例追到 Niagara 实现

## 选择对象与证据

从演示地图中的组件、Blueprint / Gameplay Cue / AnimNotify 或 Asset Registry 类与依赖查找实际使用的包，包含插件挂载点。文件名前缀只用来找候选。在特效包中覆盖各系统及变体，在玩法、场景、工具混合包中追代表性效果和存在差异的实现。沿用项目原有资产覆盖要求。

| 手头材料 | 可以回答 | 下一步 |
|---|---|---|
| 可在匹配编辑器加载的 System / Emitter | 堆栈、绑定和材质依赖 | 从编辑器核对实现，结合演示或游戏镜头解释可见贡献 |
| 已导出的 DSL 与 manifest | 导出当时的资产配置 | 对照源路径、引擎构建、源包哈希或导出时的资产记录；验证 DSL 和材质文档哈希 |
| 只有视频或帧图 | 轮廓、层间遮挡、节拍、相机相对运动 | 用参考帧支持视觉判断，列出几个可能实现及可区分它们的测试 |
| 旧包、缺依赖、只有 Cascade / 材质 | 已能核实的类、调用、引用和素材 | 说明可读范围，按原技术报告。只有确有迁移需求时才给 Niagara 对应做法 |

## 在 UE 编辑器中反查

1. 从演示关卡选中实际使用的组件，或在内容浏览器用 Reference Viewer 找调用者与依赖。打开实际的 Blueprint、Gameplay Cue 或 AnimNotify，核对触发、附着方式、变换、生命周期和对 `User.*` 的赋值。
2. 打开 Niagara System，按 System、Emitter、Particle 切分堆栈。记录发射器启用状态、Sim Target、Local Space、模块启用状态及静态开关。展开活跃的模块输入，追默认值、参数绑定、动态输入，以及需要由宿主覆写的值。
3. 打开 Renderer 实际选用的材质实例，核对覆盖项，再看父材质如何用 Emissive、Opacity、UV/SubUV、纹理通道和粒子数据。检查宿主运行时的材质覆写。移动拖尾应在有运动宿主的关卡里测试，记录停发、急转和瞬移后的表现。

## 用随附脚本读文本快照

在技能根目录运行下面的命令。把样例目录换成你拿到的导出目录，里面应有 `manifest.json` 和清单引用的相对路径文档。随附的匿名拖尾样例是手写的，用于练习取证和试跑脚本。脚本使用 Python 3.10+ 标准库，可读取 Niagara2DSL 0.4 / 0.5 清单，无需安装导出插件。若需要生成新的文本快照，可使用你的项目已安装且版本匹配的导出器，也可以在编辑器里完成上面的分析。

```powershell
python -B scripts/inspect_export.py assets/trail-export --input 'Spawn Spacing' --input 'Use Spawn Probability' --input 'Spawn Probability'
```

脚本核对文档的相对路径、SHA-256 和主资产标识，再列出含有效输入的调用和源行号。用 `--input` 指定要查看的输入名，可以重复传入。去掉该选项时输出模块索引。完整执行顺序、材质语义和运行值应结合原图或运行证据核对。匿名样例保留了关闭的发射概率开关及其隐藏数值。结果会给出采样间距与开关值，并跳过隐藏的概率数值。

1. 从 manifest 的 `document.path` 和 `materials[].used_by` 开始。用文本搜索定位 `(emitter $`、`(renderer $`、`(stage-output`、`(effective-input `，再读相邻作用域。不要按列出函数的顺序还原执行顺序。
2. 确认 System 状态、Emitter handle 与启用状态、`bLocalSpace`、SimTarget、当前 stage-output。按 Parameter Map 连接和 stage usage 追执行路径。独立 GPU stage / event 还要匹配 usage ID。把禁用节点、静态隐藏的旧值、其他阶段共享的图分开。
3. 定位目标输入的 `effective-input`。核对 `module-state`、`branch-state`、`value-status` 和 source。沿选中的链接、动态输入、此前写入、默认 Binding 或 Rapid Iteration 解释数值，保留单位。看到 `Particles.Initial.*` 时追 Spawn 的捕获值；遇到 `unresolved` 或函数展开上限时保留未知。宿主覆写要另找调用方证据。
4. 从每个启用 Renderer 的实际绑定，追到 manifest 对应材质、实例覆盖或父材质的 Emissive、Opacity、UV / SubUV、通道与贴图。多 Renderer 可能共享同一批粒子。材质实参或静态开关可以改变哪个输入最终可见。
5. 写一个可以区分解释的验证动作。例如按距采样的拖尾要移动组件，固定速度后改变速度或停止；保持相机、背景、种子不变，对比轨迹、尾部消退及瞬移断带。对照画面写出发生变化的部分。

### 可选的 Niagara2DSL 导出

若当前项目已经启用了兼容的 Niagara2DSL 导出器，可从目标项目选定引擎命令 `$editor`、项目文件 `$project`、资产的 Unreal 包名 `$asset` 和一个新输出目录 `$out`。核对所用版本的命令参数。若需要材质全文，确认导出器和材质提供器支持该能力。缺少材质文档时，保留引用和导出诊断，再在 UE 编辑器打开材质验证。

```powershell
& $editor $project '-run=Niagara2DSLExport' "-Asset=$asset" "-Output=$out" -NoEditable -unattended -NullRHI
if ($LASTEXITCODE -ne 0 -or !(Test-Path (Join-Path $out 'manifest.json'))) {
    throw 'Niagara2DSL 导出失败或未生成清单'
}
python -B scripts/inspect_export.py $out --input Lifetime
```

## 报告模板

保存到任务指定的位置，记录以下字段。

| 字段 | 填写内容 |
|---|---|
| 对象与覆盖 | System、调用者、引擎版本、已查和待查变体 |
| 画面节拍 | 触发、主体、残留，附帧号或时间码、镜头和宿主输入 |
| 实现与证据 | 每层的模块、有效输入、绑定、材质输出和证据等级，附源行号或编辑器位置 |
| 最小重制方案 | 要保留的视觉信息、预计粒子预算、可替代做法，以及可验证推断的操作 |

保留源资产供只读分析，逐层开关或更换参数的试验在副本上做。
