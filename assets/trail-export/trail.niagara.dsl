; Handwritten example with relative identifiers for offline inspection.
(niagara-dsl :version "0.1" :source "Example/FX/NS_SampleTrail"
  (system $system :asset "Example/FX/NS_SampleTrail"
    (emitter $trail :name "Trail" :enabled true
      (emitter-settings :simulation "CPUSim"
        (property :name "bLocalSpace" :value "false"))
      (script :usage "EmitterUpdateScript"
        (effective-inputs
          (effective-input :function "SpawnPerUnit" :node "$spawn" :input "Spawn Spacing"
            :module-state "enabled-on-stage" :value-status "authored-value"
            :branch-state "active" :source "callsite-literal"
            (literal :value "12.0"))
          (effective-input :function "SpawnPerUnit" :node "$spawn" :input "Use Spawn Probability"
            :module-state "enabled-on-stage" :value-status "authored-value"
            :branch-state "active" :source "callsite-literal"
            (literal :value "false"))
          (effective-input :function "SpawnPerUnit" :node "$spawn" :input "Spawn Probability"
            :module-state "enabled-on-stage" :value-status "inactive-branch"
            :branch-state "inactive" :source "callsite-literal"
            (literal :value "0.5"))))
      (renderer $ribbon :index "0" :class "NiagaraRibbonRendererProperties" :enabled true
        (material-reference :asset "Example/FX/MI_SampleTrail" :resolution "reference-only")))))
