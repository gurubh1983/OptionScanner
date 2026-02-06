/**
 * UI rule graph types. Converts to/from scanner AST (ScanRuleAST).
 */

export type LeafBlock = {
  id: string;
  type: 'leaf';
  field: string;
  operator: string;
  value?: number;
  compare?: string;
  n?: number;
};

export type CompositeBlock = {
  id: string;
  type: 'composite';
  logic: 'AND' | 'OR';
  children: RuleBlock[];
};

export type RuleBlock = LeafBlock | CompositeBlock;

export function isLeaf(b: RuleBlock): b is LeafBlock {
  return b.type === 'leaf';
}

export function isComposite(b: RuleBlock): b is CompositeBlock {
  return b.type === 'composite';
}

/** Scanner AST (API payload). */
export type LeafRuleAST = {
  field: string;
  operator: string;
  value?: number;
  compare?: string;
  n?: number;
};

export type CompositeRuleAST = {
  logic: 'AND' | 'OR';
  rules: (LeafRuleAST | CompositeRuleAST)[];
};

export type ScanRuleAST = {
  name: string;
  timeframe: string;
  logic: 'AND' | 'OR';
  rules: (LeafRuleAST | CompositeRuleAST)[];
};

/** Convert UI graph → scanner AST (strip ids). */
export function ruleBlockToAST(block: RuleBlock): LeafRuleAST | CompositeRuleAST {
  if (isLeaf(block)) {
    const out: LeafRuleAST = { field: block.field, operator: block.operator };
    if (block.value != null) out.value = block.value;
    if (block.compare) out.compare = block.compare;
    if (block.n != null) out.n = block.n;
    return out;
  }
  return {
    logic: block.logic,
    rules: block.children.map(ruleBlockToAST),
  };
}

/** Convert root (composite) + name/timeframe → full ScanRuleAST. */
export function toScanRuleAST(
  name: string,
  timeframe: string,
  root: CompositeBlock
): ScanRuleAST {
  return {
    name,
    timeframe,
    logic: root.logic,
    rules: root.children.map(ruleBlockToAST),
  };
}

/** Convert AST → UI graph (for load template). */
export function astToCompositeBlock(ast: CompositeRuleAST): CompositeBlock {
  return {
    id: crypto.randomUUID(),
    type: 'composite',
    logic: ast.logic,
    children: ast.rules.map(r => astNodeToBlock(r)),
  };
}

function astNodeToBlock(node: LeafRuleAST | CompositeRuleAST): RuleBlock {
  if ('logic' in node && 'rules' in node) {
    return {
      id: crypto.randomUUID(),
      type: 'composite',
      logic: node.logic,
      children: node.rules.map(astNodeToBlock),
    };
  }
  const n = node as LeafRuleAST;
  return {
    id: crypto.randomUUID(),
    type: 'leaf',
    field: n.field,
    operator: n.operator,
    value: n.value,
    compare: n.compare,
    n: n.n,
  };
}

/** Create empty root composite. */
export function emptyRoot(): CompositeBlock {
  return {
    id: crypto.randomUUID(),
    type: 'composite',
    logic: 'AND',
    children: [],
  };
}

/** Create default leaf block. */
export function defaultLeaf(): LeafBlock {
  return {
    id: crypto.randomUUID(),
    type: 'leaf',
    field: 'rsi(14)',
    operator: '>',
    value: 60,
  };
}

/** Parent id for root's children. */
export const ROOT_PARENT_ID = 'root' as const;

/** Get children of a composite by parentId (ROOT_PARENT_ID = root). */
export function getChildren(root: CompositeBlock, parentId: string): RuleBlock[] | null {
  if (parentId === ROOT_PARENT_ID) return root.children;
  for (const c of root.children) {
    if (isComposite(c) && c.id === parentId) return c.children;
    if (isComposite(c)) {
      const inner = getChildren(c, parentId);
      if (inner) return inner;
    }
  }
  return null;
}

/** Set children of a composite by parentId; returns new root (immutable). */
export function setChildren(
  root: CompositeBlock,
  parentId: string,
  newChildren: RuleBlock[]
): CompositeBlock {
  if (parentId === ROOT_PARENT_ID) return { ...root, children: newChildren };
  return {
    ...root,
    children: root.children.map(c =>
      isComposite(c)
        ? c.id === parentId
          ? { ...c, children: newChildren }
          : setChildren(c, parentId, newChildren)
        : c
    ),
  };
}

function findBlockIn(
  parent: CompositeBlock,
  blockId: string,
  parentId: string
): { parentId: string; index: number; block: RuleBlock } | null {
  for (let i = 0; i < parent.children.length; i++) {
    const c = parent.children[i];
    if (c.id === blockId) return { parentId, index: i, block: c };
    if (isComposite(c)) {
      const inner = findBlockIn(c, blockId, c.id);
      if (inner) return inner;
    }
  }
  return null;
}

/** Find block by id; returns parentId, index, and block. */
export function findBlock(
  root: CompositeBlock,
  blockId: string
): { parentId: string; index: number; block: RuleBlock } | null {
  return findBlockIn(root, blockId, ROOT_PARENT_ID);
}

/** Whether composite (or its subtree) contains a node with id. */
export function containsBlock(composite: CompositeBlock, nodeId: string): boolean {
  if (composite.id === nodeId) return true;
  return composite.children.some(c =>
    isComposite(c) ? containsBlock(c, nodeId) : c.id === nodeId
  );
}

/** Move block from (sourceParentId, sourceIndex) to (targetParentId, targetIndex). Immutable. */
export function moveBlock(
  root: CompositeBlock,
  sourceParentId: string,
  sourceIndex: number,
  targetParentId: string,
  targetIndex: number
): CompositeBlock {
  const children = getChildren(root, sourceParentId);
  if (!children || sourceIndex < 0 || sourceIndex >= children.length) return root;
  const [removed] = children.slice(sourceIndex, sourceIndex + 1);
  const rest = [...children.slice(0, sourceIndex), ...children.slice(sourceIndex + 1)];
  let newRoot = setChildren(root, sourceParentId, rest);
  const targetChildren = getChildren(newRoot, targetParentId) ?? [];
  let insertIndex = targetIndex;
  if (sourceParentId === targetParentId && sourceIndex < targetIndex) insertIndex = targetIndex - 1;
  const newTargetChildren = [
    ...targetChildren.slice(0, insertIndex),
    removed,
    ...targetChildren.slice(insertIndex),
  ];
  return setChildren(newRoot, targetParentId, newTargetChildren);
}
