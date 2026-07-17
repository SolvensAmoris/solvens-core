from lark import Transformer, v_args, Tree
from cosmos.compiler.errors import InternalCompileError


@v_args(inline=True)
class CosmosTransformer(Transformer):
    def string(self, token):
        return token[1:-1]  # Quita comillas

    def number(self, token):
        return float(token)

    def identifier(self, token):
        return token.value

    def position(self, x, y):
        return {"position": {"x": x, "y": y}}

    def version(self, value):
        return {"version": value}

    def author(self, value):
        return {"author": value}

    def standard(self, value):
        return {"standard": value}

    def sun(self, name):
        return {"sun": name}

    def mass(self, value):
        return {"mass": value}

    def from_clause(self, ident):
        return {"from": ident}

    def to_clause(self, ident):
        return {"to": ident}

    def flow_clause(self, flow_type):
        return {"flow": flow_type.value if hasattr(flow_type, 'value') else flow_type}

    def expiry_clause(self, date_str):
        return {"restringido_hasta": date_str}

    def planet(self, name, orbit_id, *args):
        body = {}
        for arg in args:
            if isinstance(arg, dict):
                body.update(arg)
        if not body:
            raise InternalCompileError("E998", "PARSER", f"planet body must be dict, got {type(body)}")
        return {"name": name, "orbit_id": orbit_id, **body}

    def galaxy(self, name, orbit_id, *args):
        data = {"name": name, "orbit_id": orbit_id, "planets": []}
        for arg in args:
            if isinstance(arg, dict):
                if "position" in arg:
                    data["position"] = arg["position"]
                elif "name" in arg:  # planet
                    data["planets"].append(arg)
        return {"galaxy": data}

    def light(self, *args):
        node = {}
        for arg in args:
            if isinstance(arg, dict):
                node.update(arg)
        return {"light": node}

    def metadata(self, *args):
        meta = {}
        for arg in args:
            if isinstance(arg, dict):
                meta.update(arg)
        return {"metadata": meta}

    def universe(self, name, *args):
        ast = {"universe": name, "metadata": {}, "galaxies": [], "lights": [], "sun": None}
        for arg in args:
            if isinstance(arg, dict):
                if "metadata" in arg:
                    ast["metadata"] = arg["metadata"]
                elif "galaxy" in arg:
                    ast["galaxies"].append(arg["galaxy"])
                elif "light" in arg:
                    ast["lights"].append(arg["light"])
                elif "sun" in arg:
                    ast["sun"] = arg["sun"]
                elif "version" in arg:
                    ast["metadata"]["version"] = arg["version"]
                elif "author" in arg:
                    ast["metadata"]["author"] = arg["author"]
                elif "standard" in arg:
                    ast["metadata"]["standard"] = arg["standard"]
        return ast

    def start(self, *args):
        for arg in args:
            if isinstance(arg, dict) and "universe" in arg:
                return arg
        return {}
