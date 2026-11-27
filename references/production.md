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

## 在 UE 中制作和验收

1. 在目标项目启用 Niagara，新建 Niagara System 和所需的发射器。在 System 层设置触发、生命周期及公开参数。在 Emitter Update 设置发射行为，如 Burst、Rate 或 PerUnit。在 Particle Spawn 初始化位置、颜色、尺寸、寿命和初速度。在 Particle Update 设置年龄、运动及曲线，需要时加求解模块。由 Renderer 绑定材质和粒子属性。
2. 把 `User.*` 参数绑定到实际读取它的模块，在组件或关卡中分别用默认值和一个测试值确认受控。编译、保存、重新打开资产，核对启用的层、堆栈、Renderer 和材质。在测试关卡触发系统并保存对照帧。需要 Cook、平台验证或并发计数时按目标项目的运行环境验证。
3. 用实际时间轴或固定帧率对照画面。需要速度、骨骼、深度、距离场的效果应提供对应输入，移动特效应使用会移动的宿主。检查亮暗背景、占屏尺寸和遮挡。区分渲染预热与实际模拟帧。GPU 粒子计数注明回读来源。末帧预期全黑时，用先前的可见帧以及回收时的计数确认资产曾绘制并自然消失。

交付记录包括原始需求、资产或配方位置、UE 构建、驱动参数、帧号与帧率、相机及观察到的差异。无法启动引擎时仍可检查配方和现有证据，说明哪些阶段已有回执。

## 双束汇聚信标示例

从两个本地空间 CPU Sprite 发射器开始。两侧在局部 X 轴的 −48 / +48 cm 发射，以 80 cm/s 向中线靠拢，同时以 120 cm/s 上升。寿命 0.6 s，终点在中央约 72 cm 高处。两个发射器的 Spawn Rate 共用 `User.EmissionRate`，默认各 15 粒/秒。宿主把它调到 0 后，现有粒子应在约 0.6 s 内消失。默认稳态估算为 2 × 15 × 0.6 = 18 粒，实际峰值和画面需在引擎内验证。

### 可选的 Niagara-UE-Lite 流程

若已安装匹配目标 UE 版本的 Niagara-UE-Lite，先运行 `capabilities`、`api` 确认可用命令。用 `catalog --kind` 和 `schema --kind module --asset` 获取实际资产标识及模块输入。先核对环境中的 `NIAGARA_LITE_PROJECT`，该变量优先于 `--workspace`。

在技能根目录用 Python 3.10+ 将[示例模板](../assets/converging-beacon.json)转换成 `ue-niagara-recipe/1` 文件。转换器为模板中的引擎模块、类和材质补上 Unreal 对象标识所需的挂载语法。使用本机的 `niagara-cli`，为 `$asset` 输入目标环境下从内容浏览器复制的 Niagara System 包名，或为新 System 选定包名。命令失败时先处理返回错误，再执行下一步。

```powershell
$cli = (Get-Command niagara-cli -ErrorAction Stop).Source
$work = './niagara-work'
$recipe = './beacon.generated.json'
$asset = Read-Host '目标 Niagara System 包名'
python -B scripts/prepare_beacon_recipe.py $recipe
& $cli --workspace $work init
& $cli --workspace $work create --asset $asset --recipe $recipe
& $cli --workspace $work compile --asset $asset
& $cli --workspace $work save --asset $asset
& $cli --workspace $work read --asset $asset --out (Join-Path $work 'beacon-read.json')
```

用返回的 `ok`、`compileValid` 和原生包回读核验。用 `edit` 时依据实际快照中的模块名或 GUID 定位改动。若版本支持离屏验证，可用 `cook --package` 打包，再对同一包用 `render --package` 采集多帧。核对相机、预热、粒子种子和图片。如需移动宿主，转到测试关卡采样。

## 方法来源

- PixelFX 的作者流程给出了可直接搬到制作现场的提问：特效在哪一拍读得出、游戏相机下轮廓有多大、已有变体能否解决需求。把参考、连续帧和动作事件一起比较。[创作流程](https://github.com/patch-gg/pixelfx/blob/main/skills/pixelfx/SKILL.md) · [冰霜扩散示例](https://github.com/patch-gg/pixelfx/blob/main/src/fx/ice/frost-nova.js)
- Effekseer 的设计简报为每层写清视觉职责和验收画面；其评审按节拍和参考图审视同一次构建。把程序化运动、图集主体和二者组合的选择落实到 Niagara，并保留素材、引擎绑定和画面的证据链。[设计简报](https://github.com/kanaworksai-hue/effekseer-vfx-skill/blob/main/skills/effekseer-vfx/references/design.md) · [参考片段对照](https://github.com/kanaworksai-hue/effekseer-vfx-skill/blob/main/skills/effekseer-vfx/references/reference.md) · [画面评审](https://github.com/kanaworksai-hue/effekseer-vfx-skill/blob/main/skills/vfx-review/SKILL.md)
