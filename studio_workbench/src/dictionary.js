export const OPERATOR_DICTIONARY = [
  {
    id: "input",
    displayName: "Input",
    shape: "circle",
    order: 0,
    semantic: { role: "source", builderOperation: null },
    description: "Declares the canonical source asset and source precondition."
  },
  {
    id: "normalize",
    displayName: "Normalize",
    shape: "triangle",
    order: 1,
    semantic: { role: "transform", builderOperation: "image_normalize" },
    description: "Places the source on an exact canvas using explicit anchors."
  },
  {
    id: "palette",
    displayName: "Palette",
    shape: "square",
    order: 2,
    semantic: { role: "transform", builderOperation: "palette_enforce" },
    description: "Maps visible pixels to the approved deterministic palette."
  },
  {
    id: "contact-sheet",
    displayName: "Contact Sheet",
    shape: "diamond",
    order: 3,
    semantic: { role: "preview", builderOperation: "contact_sheet" },
    description: "Renders a nearest-neighbor sequence overview."
  },
  {
    id: "godot",
    displayName: "Godot",
    shape: "arrow",
    order: 4,
    semantic: { role: "integration", builderOperation: "godot_spriteframes_compile" },
    description: "Compiles ordered frames and event metadata into Godot resources."
  },
  {
    id: "package",
    displayName: "Package",
    shape: "zigzag",
    order: 5,
    semantic: { role: "delivery", builderOperation: "package_zip" },
    description: "Assembles a byte-reproducible delivery archive."
  }
];

export const MODIFIER_DICTIONARY = [
  { id: "strict", displayName: "Strict", shape: "plus", semantic: { failOnDiagnostics: true } },
  { id: "evidence", displayName: "Evidence", shape: "check", semantic: { requirePostconditions: true } },
  { id: "parallel", displayName: "Parallel", shape: "parallel-lines", semantic: { schedulingIntent: "parallel" } }
];

export const OPERATOR_BY_ID = new Map(OPERATOR_DICTIONARY.map(item => [item.id, item]));
export const MODIFIER_BY_ID = new Map(MODIFIER_DICTIONARY.map(item => [item.id, item]));
