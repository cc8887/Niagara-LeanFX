# 从 Fab 样例追到 Niagara 实现

## 选择对象与证据

从演示地图中的组件、Blueprint / Gameplay Cue / AnimNotify 或 Asset Registry 类与依赖查找实际使用的包，包含插件挂载点。文件名前缀只用来找候选。在特效包中覆盖各系统及变体，在玩法、场景、工具混合包中追代表性效果和存在差异的实现。沿用项目原有资产覆盖要求。

| 手头材料 | 可以回答 | 下一步 |
|---|---|---|
| 可在匹配编辑器加载的 System / Emitter | 堆栈、绑定和材质依赖 | 用导出、保存回读核对实现，结合演示或游戏镜头解释可见贡献 |
| 已导出的 DSL 与 manifest | 导出当时的资产配置 | 对照源路径、引擎构建、源包哈希或导出时的资产记录；验证 DSL 和材质文档哈希 |
| 只有视频或帧图 | 轮廓、层间遮挡、节拍、相机相对运动 | 用参考帧支持视觉判断，列出几个可能实现及可区分它们的测试 |
| 旧包、缺依赖、只有 Cascade / 材质 | 已能核实的类、调用、引用和素材 | 说明可读范围，按原技术报告。只有确有迁移需求时才给 Niagara 对应做法 |

## GASP58 只读导出

从 GASP58 根目录运行。先用项目的引擎构建与已挂载包路径，选择一个新输出目录。下面以 Lyra 移动拖尾为例。历史快照可从 `Saved/Niagara2DSL` 中按 `manifest.json` 的 `source_asset` 定位。

```powershell
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$project = (Resolve-Path GASP58.uproject).Path
$out = Join-Path (Resolve-Path Saved).Path ('Niagara2DSL/FabTrail-' + [guid]::NewGuid().ToString('N'))
& $editor $project '-run=Niagara2DSLExport' '-Asset=/Game/Effects/Particles/Explosion/NS_Grenade_Trail' "-Output=$out" -FunctionDepth=1 -NoEditable -VerifyDeterminism -unattended -nop4 -nosplash -NullRHI -nosound '-DisablePlugins=MCPServer,Mocara' '-ini:Editor:[/Script/MatBP2FPEditor.MatBP2FPSettings]:AutoSyncMode=None' '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
if ($LASTEXITCODE -ne 0 -or !(Test-Path (Join-Path $out manifest.json))) { throw "Niagara export incomplete: $out" }
python Plugins/Niagara2DSL/Scripts/verify_export.py "$out" --schema Doc/Niagara2DSLContracts/export-manifest.schema.json
```

先读 `Plugins/Niagara2DSL/README.md` 确认当前接口。需要完整材质导出时加 `-RequireMaterials`。缺少 provider 时保留材质引用和诊断，回到 MatBP2FP 或可用的父材质 / 实例资料。记录校验结果中的 `json_schema` 是否真正执行。若命令未写 manifest，改用可核对版本的旧快照或降低证据等级。宿主蓝图与动画仍使用原有 BlueprintLisp / AnimBP2FP 分析链。

## 在大快照里找关键链路

从 GASP58 根目录，可在验证成功后提取按作用域整理的索引。去掉 `--input` 时输出模块索引，重复该选项可取指定输入及原文行号。

```powershell
python -B Skills/niagara-vfx-production/scripts/inspect_export.py "$out" --project . --input 'Spawn Spacing' --input 'Use Spawn Probability' --input Lifetime
```

索引列出含有效输入的调用，无输入模块及完整执行顺序回原图核对。关闭的发射器和 Renderer 仍列有状态；选中值的动态表达式、默认绑定及其依赖要沿行号进入 DSL。举例来说，应同时核对 Spawn Probability 数值和 Use Spawn Probability 开关。

1. 从 manifest 的 `document.path` 和 `materials[].used_by` 开始。用文本搜索定位 `(emitter $`、`(renderer $`、`(stage-output`、`(effective-input `，再读相邻作用域。不要按列出函数的顺序还原执行顺序。
2. 确认 System 状态、Emitter handle 与启用状态、`bLocalSpace`、SimTarget、当前 stage-output。按 Parameter Map 连接和 stage usage 追执行路径。独立 GPU stage / event 还要匹配 usage ID。把禁用节点、静态隐藏的旧值、其他阶段共享的图分开。
3. 定位目标输入的 `effective-input`。核对 `module-state`、`branch-state`、`value-status` 和 source。沿选中的链接、动态输入、此前写入、默认 Binding 或 Rapid Iteration 解释数值，保留单位。看到 `Particles.Initial.*` 时追 Spawn 的捕获值；遇到 `unresolved` 或函数展开上限时保留未知。宿主覆写要另找调用方证据。
4. 从每个启用 Renderer 的实际绑定，追到 manifest 对应材质、实例覆盖或父材质的 Emissive、Opacity、UV / SubUV、通道与贴图。多 Renderer 可能共享同一批粒子。材质实参或静态开关可以改变哪个输入最终可见。
5. 写一个可以区分解释的验证动作。例如按距采样的拖尾要移动组件，固定速度后改变速度或停止；保持相机、背景、种子不变，对比轨迹、尾部消退及瞬移断带。对照画面写出发生变化的部分。

## 写回 GASP58

在 `Doc/Fab项目分析/<项目名>.md` 的效果章节填入节拍、逐层实现、证据级别和迁移方案；`Overview/<项目名>-Overview.md` 链到这个章节。记录代表对象与已覆盖/待核实的变体。沿用当前队列的状态更新规则。分析动作只读取源资产，生产测试使用独立工作区。项目已有的 Lyra 详页包含一个可核查的拖尾实例。
