# 把分层方案做成可运行的 Niagara 特效

## 按可见任务选技术

| 可见需求 | 候选做法 | 最容易漏掉的核验 |
|---|---|---|
| 短亮点、烟团、复杂火形 | Sprite；体积细节可用带遮罩的 SubUV 图集，近景需要时混用 Mesh | 正侧轮廓、图集帧序与通道、加色过曝、透明边和深度相交 |
| 沿运动历史留下连续曲线 | 世界空间 Ribbon；按距生成或由宿主提供采样点 | RibbonID / LinkOrder、宽度绑定、UV 铺设、静止与瞬移 |
| 有厚度的碎片或侧面仍可读的体积 | Mesh Renderer、旋转与尺度；小屏幕远景可简化 | 透视变化、网格朝向、材质槽、剔除范围 |
| 贴地的预警圈或持续印记 | 地表贴花、切向平面或受控网格，可与 Niagara 浮粒组合 | 斜坡、台阶、投影范围，图案半径由玩法半径驱动 |
| 持续环境、附着状态、光束 | 区分跟随主体的部分与留在世界的部分；宿主按需更新端点 | 进入、稳态、停止与尾粒释放，移动主体时检查锚点 |

给每层指定亮部、主体色或暗部的职责。需要暗烟时选能压暗背景的混合方式。先通过尺寸、占屏和时间控制高光；控制透明覆盖、重复绘制、动态灯、碰撞或 Ribbon 细分时，记录对主轮廓的影响。预算以目标相机与并发实测为准。

## 粒子数预算

一次性效果按一次触发的全程累计生成量核算。以闪光弹为例，若飞行球用 1 粒、爆闪用 1 粒，则整段飞行可再生成最多 18 个拖尾粒子以满足 20 粒目标。已经消亡的拖尾粒子仍计入累计量。持续循环效果按同一时刻各层存活数之和取峰值。

- 从最少独立运动单元开始。同心环、星芒和同步碎光先试单个 Sprite 的材质或 SubUV。需要分别绕障、碰撞或随视角产生视差的形状再拆粒子。多个 Renderer 共用的粒子只计一次，绘制开销另记。
- 逐层记录单次 Burst 数、连续生成速率（粒/秒）或采样间距（厘米/粒）、寿命、有效发射时长。匀速连续发射且寿命固定时，单层同时存活峰值可按 `ceil(速率 × min(寿命, 发射时长))` 粗估。Burst、循环或重复触发按时间窗叠加仍存活的批次。区分一次播放累计生成量、单实例同时存活峰值和场景并发峰值。缺少实测时保留估算标记。
- 移动拖尾优先试少量世界空间 Ribbon 控制点或按距采样。每个由粒子提供的控制点都计入预算。按最高预期速度、最急转角和目标镜头测试，逐步放大采样间距，直到出现断带、折角或尾长偏差。停步、瞬移时也要检查。若接口只支持定频生成，可按速度和允许间距换算速率再比较。
- 固定相机、宿主轨迹、随机种子及关键时刻，对比低档与当前档，查看首帧辨识度、最急转弯、爆发轮廓及淡出。先降低生成数，出现可指认的画面退化时再加回。交付记录选用档、试过的更低档及差异，同时检查透明覆盖、材质成本与并发帧耗。运行条件不足时分别标明已验证的画面和待测成本。

## UE / Niagara-UE-Lite

在项目匹配版本的 UE 编辑器中可直接按下面的堆栈逻辑制作。使用 Lite 时先运行 `capabilities`、`api`，并读本机版本的 `docs/template-free-authoring.md`。有源码目录时查找对应发行包或已配置的原生后端；源码 checkout 本身通常缺少发行包的 Project 与 backend。5.8 与 5.9 的原生文档、项目和缓存应各用匹配版本。

1. 给新资产选独立 `/Game/…` 包名。在 Lite 新工作区执行 `init`，用 `catalog --kind modules/materials/renderers`（每次一个 kind）找路径，`schema --kind module --asset <对象路径>` 查实际输入、类型与默认值。已有系统或发射器可以在同版本副本中复用。确认 `NIAGARA_LITE_PROJECT` 指向预计的工作区，显式设置时它优先于 `--workspace`。
2. 用 `ue-niagara-recipe/1` 操作组织系统。System 负责触发、生命周期和公开输入；Emitter Update 负责周期与 Burst/Rate/PerUnit；Particle Spawn 初始化位置、颜色、尺寸、寿命及初速度；Particle Update 控制年龄、运动与曲线；Renderer 显式绑定材质和粒子属性。按图需要加入求解，不要同时用手写积分和求解模块重复移动。
3. 通过 `create --asset ... --recipe ...` 创建，后续使用 `edit`。用实际快照中的模块名称或 GUID 定位修改。把共享参数从宿主到真正读它的模块连通，分别改变默认值和一个测试值。Lite 支持绑定已有材质；新材质图可在 UE 或材质工具制作后连同依赖导入。常量属性 / 声明但未绑定的 User 参数无法单独实现动画。
4. `compile`、`save`、新进程 `read`，核对实际包、启用的层、堆栈和 renderer/material。用 `cook --package <新目录>` 一次打包，再用 `render --package ... --frames N --out <新文件>.png` 在同一包采多帧；设置一致的视口、warmup 和种子。核对返回码、JSON 内的 ok、资产路径、相机/渲染信息、图片内容。新建空系统只验证了编辑接口。
5. 打开帧图并按原始时间轴看运动。用预览程序固定步长将帧号换算成时间；区分渲染预热和实际模拟帧。在目标地图补查亮暗背景、尺度及遮挡。基于速度/骨骼/深度/距离场的特效需要相应输入；独立预览的静止组件无法复现移动宿主。GPU 粒子计数注明回读来源。尾帧预期全黑而工具返回 `black_frame` 时，另取粒子数或场景背景对照，单独判断资源加载、绘制和自然消失。

最小的记录包含原始 brief、资产或配方位置、UE 构建、测试时驱动的外部参数、帧号/fps、相机以及观察到的最大偏差。无法启动引擎时仍可检查配方协议和既有证据，明确哪些生产阶段有实际回执。

## 可执行配方示例

[双束汇聚信标](../assets/converging-beacon.json) 的设计目标是让一个持续拾取点在斜侧镜头中形成两束上升的琥珀色光点。两侧在局部 X 轴的 −48 / +48 cm 发射，以 80 cm/s 向中线靠拢，同时以 120 cm/s 上升；按 0.6 s 的初始寿命计算，轨迹终点在中央约 72 cm 高处。两个 CPU Sprite 发射器共用 `User.EmissionRate`，默认各 15 粒/秒。宿主随时可以把它调到 0，保留在场粒子的剩余寿命。以下操作在匹配的 5.8.1 Lite 发行包上执行，`$cli` 为可执行文件路径，`$work` 为独立工作区，`$recipe` 为配方绝对路径。

```powershell
& $cli --workspace $work init
& $cli --workspace $work create --asset /Game/VFXLab/NS_ConvergingBeacon --recipe $recipe
& $cli --workspace $work compile --asset /Game/VFXLab/NS_ConvergingBeacon
& $cli --workspace $work save --asset /Game/VFXLab/NS_ConvergingBeacon
& $cli --workspace $work read --asset /Game/VFXLab/NS_ConvergingBeacon --out (Join-Path $work 'beacon-read.json')
```

按返回的 `ok`、`compileValid`、保存的原生包和回读结果核验；若创建失败，先处理错误再运行后续步骤。用同一包拍首次出现和稳定阶段。在玩法宿主把速率从 15 改为 0，预期约 0.6 s 后无在场粒子。按默认配置估算，理想稳态约有 2 × 15 × 0.6 = 18 粒同时存活。这个预算对应配方估算，新默认值的实际峰值和画面需在引擎内确认。

## 方法来源

- PixelFX 的作者流程给出了可直接搬到制作现场的提问：特效在哪一拍读得出、游戏相机下轮廓有多大、已有变体能否解决需求。把参考、连续帧和动作事件一起比较。[创作流程](https://github.com/patch-gg/pixelfx/blob/main/skills/pixelfx/SKILL.md) · [冰霜扩散示例](https://github.com/patch-gg/pixelfx/blob/main/src/fx/ice/frost-nova.js)
- Effekseer 的设计简报为每层写清视觉职责和验收画面；其评审按节拍和参考图审视同一次构建。把程序化运动、图集主体和二者组合的选择落实到 Niagara，并保留素材、引擎绑定和画面的证据链。[设计简报](https://github.com/kanaworksai-hue/effekseer-vfx-skill/blob/main/skills/effekseer-vfx/references/design.md) · [参考片段对照](https://github.com/kanaworksai-hue/effekseer-vfx-skill/blob/main/skills/effekseer-vfx/references/reference.md) · [画面评审](https://github.com/kanaworksai-hue/effekseer-vfx-skill/blob/main/skills/vfx-review/SKILL.md)
