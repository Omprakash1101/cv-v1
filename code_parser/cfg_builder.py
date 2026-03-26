
import ast
from graphviz import Digraph
import logging
logger = logging.getLogger(__name__)

STYLE = {
    "start_end":  dict(fillcolor="#1a1a2e", fontcolor="white",   color="#e94560", shape="oval"),
    "process":    dict(fillcolor="#16213e", fontcolor="#e0e0e0", color="#0f3460", shape="box"),
    "decision":   dict(fillcolor="#0f3460", fontcolor="white",   color="#e94560", shape="diamond"),
    "io":         dict(fillcolor="#533483", fontcolor="white",   color="#e94560", shape="box"),
    "print_io":   dict(fillcolor="#533483", fontcolor="white",   color="#e94560", shape="parallelogram"),
    "func_entry": dict(fillcolor="#e94560", fontcolor="white",   color="#c73652", shape="oval"),
    "func_exit":  dict(fillcolor="#e94560", fontcolor="white",   color="#c73652", shape="oval"),
}


class CFGBuilder(ast.NodeVisitor):

    def __init__(self):
        self.dot = Digraph()
        self.dot.attr(rankdir="TB", bgcolor="#0a0a1a",
                      fontname="Courier New", splines="polyline",
                      nodesep="0.5", ranksep="0.6")
        self.dot.attr("node", fontname="Courier New", fontsize="11",
                      style="filled", margin="0.2,0.1")
        self.dot.attr("edge", color="#4a90d9", fontcolor="#aaaaaa",
                      fontname="Courier New", fontsize="9", penwidth="1.5")

        self._ctr      = 0
        self.functions = {}
        self.func_exits= {}
        self.cur_func  = None
        self.loop_stack= []
        self.vars      = {}
        self.cur = self._node("Start", "start_end")

    # ── primitives ──────────────────────────────────────────────────────────

    def _node(self, label, sk="process"):
        self._ctr += 1
        nid = f"N{self._ctr}"
        s = STYLE[sk]
        extra = {"style": "filled,rounded"} if s["shape"] == "box" else {"style": "filled"}
        self.dot.node(nid, label,
                      fillcolor=s["fillcolor"], fontcolor=s["fontcolor"],
                      color=s["color"], shape=s["shape"], **extra)
        return nid

    def _edge(self, a, b, **kw):
        if a and b:
            self.dot.edge(a, b, **kw)

    # ── branch execution: visits stmts, first edge from 'origin' is colored ─

    def _branch(self, origin, stmts, label="", color="#4a90d9"):
        #Visit stmts. The first edge that would be drawn FROM origin
        #gets label/color applied. Returns final self.cur.
        self.cur = origin
        intercepted = [False]

        real_edge = self.dot.edge
        def patched(a, b, **kw):
            if not intercepted[0] and a == origin:
                intercepted[0] = True
                kw.setdefault("label", label)
                kw["color"] = color
                kw["fontcolor"] = color
            real_edge(a, b, **kw)

        self.dot.edge = patched
        for stmt in stmts:
            if self.cur is None: break
            self.visit(stmt)
        self.dot.edge = real_edge

        # If no statements executed (empty branch), draw a phantom edge
        # so the label still appears — but only if label is set
        if not intercepted[0] and label and stmts == []:
            pass   # empty branch handled by caller

        return self.cur

    def _handle_function_call(self, parent_node, fname):
        #Handles both normal and recursive function calls properly

        cont = f"J{self._ctr+1}"
        self._ctr += 1

        self.dot.node(
            cont, "",
            shape="point",
            fillcolor="#4a90d9",
            color="#4a90d9",
            style="filled",
            width="0.08"
        )

        is_recursive = (fname == self.cur_func)

        if is_recursive:
            # 🔁 RECURSIVE CALL
            self._edge(parent_node, self.functions[fname],
                    color="#ff9800", penwidth="2",
                    label="recursive call")
            

        else:
            # Normal call
            self._edge(parent_node, self.functions[fname],
                    style="dashed", color="#e94560",
                    label="call")

        return cont

    # ════════════════════════════════════════════════════════════════════════
    # Statement visitors
    # ════════════════════════════════════════════════════════════════════════

    def visit_Assign(self, node):
        if self.cur is None:
            return

        n = self._node(ast.unparse(node), "process")
        self._edge(self.cur, n)
        self.cur = n

        # 🔥 NEW: Track simple constant assignments
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            value = self._eval(node.value)
            if value is not None:
                self.vars[var_name] = value

        # Detect function call inside assignment
        for child in ast.walk(node.value):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                fname = child.func.id
                if fname in self.functions:
                    cont = f"J{self._ctr+1}"
                    self._ctr += 1
                    self.dot.node(
                        cont, "",
                        shape="point",
                        fillcolor="#4a90d9",
                        color="#4a90d9",
                        style="filled",
                        width="0.08"
                    )

                    self.cur = self._handle_function_call(n, fname)
                    break

    def visit_AugAssign(self, node):
        if self.cur is None: return
        ops = {ast.Add:"+", ast.Sub:"-", ast.Mult:"*", ast.Div:"/"}
        var = ast.unparse(node.target)
        op  = ops.get(type(node.op), "?")
        n   = self._node(f"{var} = {var} {op} {ast.unparse(node.value)}", "process")
        self._edge(self.cur, n)
        self.cur = n

    # ── IF ───────────────────────────────────────────────────────────────────
    def _handle_condition_call(self, cond_node, test_node):
        for child in ast.walk(test_node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                fname = child.func.id
                if fname in self.functions:
                    cont = f"J{self._ctr+1}"
                    self._ctr += 1
                    self.dot.node(
                        cont, "",
                        shape="point",
                        fillcolor="#4a90d9",
                        color="#4a90d9",
                        style="filled",
                        width="0.08"
                    )
                    self.cur = self._handle_function_call(cond_node, fname)
                    break

    def visit_If(self, node):
        if self.cur is None: return

        cond = self._node(ast.unparse(node.test), "decision")
        self._edge(self.cur, cond)
        self._handle_condition_call(cond, node.test)

        # 🔥 NEW: detect function call inside condition
        for child in ast.walk(node.test):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                fname = child.func.id
                if fname in self.functions:
                    cont = f"J{self._ctr+1}"
                    self._ctr += 1
                    self.dot.node(
                        cont, "",
                        shape="point",
                        fillcolor="#4a90d9",
                        color="#4a90d9",
                        style="filled",
                        width="0.08"
                    )

                    self.cur = self._handle_function_call(cond, fname)
                    break

        true_exit  = self._branch(cond, node.body,   "True",  "#4caf50")
        false_exit = self._branch(cond, node.orelse, "False", "#f44336")

        # If the False branch is empty _branch returns cond (origin).
        # In that case we add a direct False edge from cond to merge.
        if not node.orelse:
            false_exit = cond   # will get edge to merge below

        # Merge
        if true_exit is None and false_exit is None:
            self.cur = None
        elif true_exit is None:
            self.cur = false_exit
        elif false_exit is None:
            self.cur = true_exit
        else:
            # Both live — need a merge node
            # Re-use the join as an invisible point
            join = f"J{self._ctr+1}"; self._ctr += 1
            self.dot.node(join, "", shape="point",
                          fillcolor="#4a90d9", color="#4a90d9",
                          style="filled", width="0.08")
            self._edge(true_exit, join)
            # If false_exit == cond (empty else), draw False edge to join
            if false_exit == cond:
                self.dot.edge(cond, join, label="False",
                              color="#f44336", fontcolor="#f44336")
            else:
                self._edge(false_exit, join)
            self.cur = join

    # ── WHILE ────────────────────────────────────────────────────────────────

    def visit_While(self, node):
        if self.cur is None: return

        cond = self._node(ast.unparse(node.test), "decision")
        self._edge(self.cur, cond)
        self._handle_condition_call(cond, node.test)
        
        # We need an exit node for break and False branch.
        # Create it AFTER visiting body so it appears below.
        # Use a deferred list for break nodes.
        break_sources = []
        self.loop_stack.append({"cond": cond, "breaks": break_sources})

        body_exit = self._branch(cond, node.body, "True", "#4caf50")

        self.loop_stack.pop()

        if body_exit is not None:
            self._edge(body_exit, cond, style="dashed",
                       color="#4a90d9", label="loop back")

        # Exit point — only a point node if breaks exist, otherwise
        # the False edge just goes to whatever follows.
        if break_sources:
            exit_n = f"J{self._ctr+1}"; self._ctr += 1
            self.dot.node(exit_n, "", shape="point",
                          fillcolor="#4a90d9", color="#4a90d9",
                          style="filled", width="0.08")
            self.dot.edge(cond, exit_n, label="False",
                          color="#f44336", fontcolor="#f44336")
            for bs in break_sources:
                self._edge(bs, exit_n, color="#f44336")
            self.cur = exit_n
        else:
            # No breaks — False edge goes directly to next statement
            # Store cond as cur; caller will draw edge from it
            self._pending_false = (cond, "False", "#f44336")
            self.cur = cond   # Will be updated below via _flush_false

        # Flush pending False edge if it exists
        self._flush_pending_false()

    def _flush_pending_false(self):
        #If we have a pending False edge from a while with no breaks,
        #wrap it: next node added after this will get the False edge from cond.
        if not hasattr(self, "_pending_false") or self._pending_false is None:
            return
        src, label, color = self._pending_false
        self._pending_false = None
        # Patch next _edge call from src
        real_edge = self.dot.edge
        applied = [False]
        def patched(a, b, **kw):
            if not applied[0] and a == src:
                applied[0] = True
                kw["label"] = label
                kw["color"] = color
                kw["fontcolor"] = color
            real_edge(a, b, **kw)
        self.dot.edge = patched
        self._restore_edge_after_next = real_edge

    # ── FOR ──────────────────────────────────────────────────────────────────

    def visit_For(self, node):
        if self.cur is None: return
        var = ast.unparse(node.target)

        if (isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == "range"):
            args = [self._eval(a) for a in node.iter.args]
            # 🔥 NEW: detect function call inside range arguments
            for arg in node.iter.args:
                for child in ast.walk(arg):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        fname = child.func.id
                        if fname in self.functions:
                            cont = f"J{self._ctr+1}"
                            self._ctr += 1
                            self.dot.node(
                                cont, "",
                                shape="point",
                                fillcolor="#4a90d9",
                                color="#4a90d9",
                                style="filled",
                                width="0.08"
                            )

                            self.cur = self._handle_function_call(self.cur, fname)
                            break
            if   len(args) == 1: start, stop, step = 0, args[0], 1
            elif len(args) == 2: start, stop, step = args[0], args[1], 1
            elif len(args) == 3: start, stop, step = args
            else: return
            self.vars[var] = start
            init = self._node(f"{var} = {start}", "process")
            self._edge(self.cur, init)
            self.cur = init
            cond_label = f"{var} < {stop}"
        else:
            cond_label = f"for {var} in {ast.unparse(node.iter)}"
            step = 1

        cond = self._node(cond_label, "decision")
        self._edge(self.cur, cond)

        break_sources = []
        self.loop_stack.append({"cond": cond, "breaks": break_sources})

        body_exit = self._branch(cond, node.body, "True", "#4caf50")
        self.loop_stack.pop()

        if body_exit is not None:
            inc = self._node(f"{var} = {var} + {step}", "process")
            self._edge(body_exit, inc)
            self._edge(inc, cond, style="dashed", color="#4a90d9", label="loop back")

        # Exit
        exit_n = f"J{self._ctr+1}"; self._ctr += 1
        self.dot.node(exit_n, "", shape="point",
                      fillcolor="#4a90d9", color="#4a90d9",
                      style="filled", width="0.08")
        self.dot.edge(cond, exit_n, label="False",
                      color="#f44336", fontcolor="#f44336")
        for bs in break_sources:
            self._edge(bs, exit_n, color="#f44336")
        self.cur = exit_n

    # ── BREAK / CONTINUE ────────────────────────────────────────────────────

    def visit_Break(self, node):
        if self.cur is None or not self.loop_stack: return
        ctx = self.loop_stack[-1]
        n = self._node("break", "io")
        self._edge(self.cur, n)
        ctx["breaks"].append(n)
        self.cur = None

    def visit_Continue(self, node):
        if self.cur is None or not self.loop_stack: return
        ctx = self.loop_stack[-1]
        n = self._node("continue", "io")
        self._edge(self.cur, n)
        self._edge(n, ctx["cond"], color="#ff9800")
        self.cur = None

    # ── EXPR ─────────────────────────────────────────────────────────────────

    def visit_Expr(self, node):
        if self.cur is None: return
        if not isinstance(node.value, ast.Call): return
        fn = node.value.func
        is_print = isinstance(fn, ast.Name) and fn.id == "print"
        label = ast.unparse(node.value)
        sk = "print_io" if is_print else "process"
        n = self._node(label, sk)
        self._edge(self.cur, n)
        self.cur = n
        for child in ast.walk(node.value):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                fname = child.func.id
                if fname in self.functions:
                    cont = f"J{self._ctr+1}"; self._ctr += 1
                    self.dot.node(cont, "", shape="point",
                                  fillcolor="#4a90d9", color="#4a90d9",
                                  style="filled", width="0.08")
                    self.cur = self._handle_function_call(n, fname)
                    break

    # ── FUNCTION DEF ─────────────────────────────────────────────────────────

    def visit_FunctionDef(self, node):
        fname = node.name
        prev_cur = self.cur; prev_vars = self.vars.copy()
        prev_func = self.cur_func;  self.cur_func = fname

        entry = self._node(f"{fname}()", "func_entry")
        self.functions[fname] = entry
        self.cur = entry

        for arg in node.args.args:
            pn = self._node(f"param: {arg.arg}", "process")
            self._edge(self.cur, pn); self.cur = pn

        exit_n = self._node(f"{fname}: Exit", "func_exit")
        self.func_exits[fname] = exit_n
        self.vars = {}

        for stmt in node.body:
            if self.cur is None: break
            self.visit(stmt)
        if self.cur is not None:
            self._edge(self.cur, exit_n)

        self.cur = prev_cur; self.vars = prev_vars; self.cur_func = prev_func

    # ── RETURN ───────────────────────────────────────────────────────────────
    def visit_Return(self, node):
        if self.cur is None:
            return

        exit_node = self.func_exits.get(self.cur_func)

        ret_text = ast.unparse(node.value) if node.value else ""
        ret_label = f"return {ret_text}".strip()

        # 🔹 Create RETURN NODE directly
        ret_node = self._node(ret_label, "io")
        self._edge(self.cur, ret_node)

        # 🔹 Detect recursive / function call inside return
        if node.value:
            for child in ast.walk(node.value):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    fname = child.func.id

                    if fname in self.functions:
                        # 🔥 DIRECT recursive call FROM RETURN NODE
                        self._edge(
                            ret_node,
                            self.functions[fname],
                            color="#ff9800" if fname == self.cur_func else "#e94560",
                            penwidth="2",
                            label="recursive call" if fname == self.cur_func else "call"
                        )

                        self.cur = None
                        return

        # 🔹 Normal return
        if exit_node:
            self._edge(ret_node, exit_node)

        self.cur = None
    def _eval(self, node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.Name): return self.vars.get(node.id)
        if isinstance(node, ast.BinOp):
            l, r = self._eval(node.left), self._eval(node.right)
            if l is None or r is None: return None
            try:
                ops={ast.Add:lambda:l+r,ast.Sub:lambda:l-r,ast.Mult:lambda:l*r,ast.Div:lambda:l/r}
                return ops.get(type(node.op), lambda: None)()
            except: return None
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "range":
                args = [self._eval(a) for a in node.args]
                try:
                    if len(args)==1: return list(range(args[0]))
                    if len(args)==2: return list(range(*args))
                    if len(args)==3: return list(range(*args))
                except: pass
        return None

    # ── FINISH ───────────────────────────────────────────────────────────────

    def finish(self):
        end = self._node("End", "start_end")
        if self.cur is not None:
            self._edge(self.cur, end)
        return self.dot


def generate_flowchart_svg(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return "", f"Syntax Error: {e}"
    try:
        b = CFGBuilder()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef): b.visit(node)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef): b.visit(node)
        dot = b.finish()
        # Remove pure pass-through point nodes
        clean_src = _remove_passthrough_points(dot.source)
        import requests

        def dot_to_svg(dot_string):
            try:
                response = requests.post(
                    "https://kroki.io/graphviz/svg",
                    data=dot_string.encode("utf-8"),
                    headers={"Content-Type": "text/plain"},
                    timeout=5
                )

                if response.status_code != 200:
                    return None, f"Kroki error: {response.status_code}"

                return response.text, None

            except Exception:
                logger.exception("dot_to_svg failed")
                return None, "internal_error"
        svg, err = dot_to_svg(clean_src)
        if err:
            logger.error("SVG generation failed\nError: %s",err)
            return "", "internal_error"
        return svg, None
    except Exception as e:
        import traceback
        logger.exception("Unexpected error in generate_flowchart_svg")
        return "", "internal_error"


def _remove_passthrough_points(dot_source: str) -> str:
    #Post-process DOT source: remove any point node that has exactly
    #1 incoming and 1 outgoing edge (pure pass-through), replacing
    #with a direct edge carrying the incoming edge's attributes.
    
    import re
    lines = dot_source.split('\n')

    # Parse all node declarations
    point_ids = set()
    for line in lines:
        m = re.match(r'\s*([NJ]\d+)\s+\[.*?shape=point.*?\]', line)
        if m:
            point_ids.add(m.group(1))

    if not point_ids:
        return dot_source

    # Parse edges: src -> dst [attrs]
    edge_re = re.compile(r'\s*(\w+)\s*->\s*(\w+)(.*)')
    edges = []
    for line in lines:
        m = edge_re.match(line)
        if m:
            edges.append((m.group(1), m.group(2), m.group(3).strip(), line))

    # Count in/out for each point node
    def counts(nid):
        inc = [(s, d, a, l) for s, d, a, l in edges if d == nid]
        out = [(s, d, a, l) for s, d, a, l in edges if s == nid]
        return inc, out

    to_remove = {}  # nid -> (in_src, in_attrs, out_dst)
    for nid in point_ids:
        inc, out = counts(nid)
        if len(inc) == 1 and len(out) == 1:
            in_src, _, in_attrs, _ = inc[0]
            _, out_dst, out_attrs, _ = out[0]
            # Use incoming attrs (they carry label/color)
            attrs = in_attrs if in_attrs else out_attrs
            to_remove[nid] = (in_src, out_dst, attrs)

    if not to_remove:
        return dot_source

    # Rebuild
    skip_nodes = set(to_remove.keys())
    skip_lines = set()
    bypass = []

    for nid, (src, dst, attrs) in to_remove.items():
        # Find lines to skip
        for line in lines:
            if re.match(rf'\s*{nid}\s+\[', line):
                skip_lines.add(line)
            m = edge_re.match(line)
            if m and (m.group(1) == nid or m.group(2) == nid):
                skip_lines.add(line)
        bypass.append(f'\t{src} -> {dst}{attrs}')

    new_lines = []
    for line in lines:
        if line in skip_lines:
            continue
        new_lines.append(line)

    # Insert bypasses before closing brace
    for i in range(len(new_lines)-1, -1, -1):
        if new_lines[i].strip() == '}':
            new_lines[i:i] = bypass
            break

    return '\n'.join(new_lines) 