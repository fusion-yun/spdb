import collections
import contextlib
from copy import copy

import jsonschema

from spdm.utils.logger import logger
from spdm.utils.uri_utils import getvalue_r, uri_join


def _extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def _properties(validator, properties, instance, schema):
        for p, subschema in properties.items():
            if (
                isinstance(subschema, collections.abc.Iterable)
                and "default" in subschema
                and hasattr(instance, "setdefault")
            ):
                instance.setdefault(p, subschema["default"])

        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return jsonschema.validators.extend(
        validator_class,
        {"properties": _properties},
    )


_DefaultValidatingValidator = _extend_with_default(jsonschema.Draft7Validator)


class RefResolver(object):
    """Resolve and fetch '$ref' in the document (json,yaml,https ...)
    schemas:
        pkgdata     :   pkgutil.get_data(o.authority or __package__,o.path)
        https,http  :   requests.get(uri).json()
        josn        :   json.load(open(uri))
        yaml        :   json.load(open(uri))
    Example(code):

        >>> repo = RefResolver()
        >>> repo.alias.append("https://fusionyun.org/schemas/draft-00/",
                    "pkgdata:///../schemas")
        >>> repo.alias.append(f"/modules/", "file://workspaces/FyPackages/modules/")
    @note
        *  compatible with jsonschema.RefResolver

    TODO (salmon 20190915): support XML,XSD,XSLT
    """

    def __init__(
        self,
        *,
        base_uri="",
        encode="UTF-8",
        prefetch=None,
        enable_remote=False,
        enable_validate=True,
        enable_envs_template=True,
        default_file_ext="yaml",
        default_schema="http://json-schema.org/draft-07/schema#",
        alias=None,
        **kwargs,
    ):
        super().__init__()

        self._alias = Alias(glob_pattern_char="*")
        self._encode = encode
        self._scopes_stack = [base_uri] if len(base_uri) > 0 and base_uri[-1] == "/" else [base_uri + "/"]
        self._default_file_ext = default_file_ext
        self._default_schema = uri_join(base_uri, default_schema)
        self._enable_remote = enable_remote
        self._enable_validate = enable_validate
        self._enable_envs_template = enable_envs_template
        if prefetch is not None:
            # if not isinstance(prefetch, pathlib.Path):
            #     prefetch = pathlib.Path(prefetch)

            # if prefetch.is_dir():
            prefetch = f"{prefetch}/" if prefetch[-1] != "/" else prefetch
            self._alias.prepend("https://", prefetch)
            self._alias.prepend("http://", prefetch)

        if alias is None:
            pass
        elif isinstance(alias, collections.abc.Mapping):
            for k, v in alias.items():
                self._alias.append(self.normalize_uri(k), v)
        elif isinstance(alias, collections.abc.Sequence):
            for k, v in alias:
                self._alias.append(self.normalize_uri(k), v)
        else:
            raise TypeError(f"Require list or map, not [{type(alias)}]")

        self._cache = {}
        self._validator = {"http://json-schema.org/draft-07/schema#": _DefaultValidatingValidator}

    @property
    def alias(self):
        return self._alias

    def normalize_uri(self, uri):
        if uri is None:
            uri = None
        elif type(uri) is str:
            pass
        elif isinstance(uri, collections.abc.Sequence):
            uri = "/".join(uri)
        else:
            raise TypeError(f"Illegal type {type(uri).__name__}")
        return uri_join(self.resolution_scope, uri)

    def remove_prefix(self, p: str):
        return self.relative_path(p)

    def relative_path(self, p: str):
        # FIXME: not complete , only support sub-path
        prefix = self.resolution_scope
        if p is None:
            return None
        elif p.startswith(prefix):
            return p[len(prefix) :].strip("/.")
        else:
            raise NotImplementedError()

    _normalize_ids = ["$schema", "$id", "$base"]

    def validate(self, doc):
        if doc is None:
            raise ValueError(f"Try to validate an empty document!")

        for nid in RefResolver._normalize_ids:
            if nid not in doc:
                continue
            doc[nid] = self.normalize_uri(doc[nid])

        schema = doc.get("$schema", None)
        if isinstance(schema, str):
            schema_id = schema
            schema = {"$id": schema_id}
        elif isinstance(schema, collections.abc.Mapping):
            schema_id = schema.get("$id", None)
        else:
            schema_id = None
            schema = {"$id": schema_id}

        validator = self._validator.get(schema_id, None)
        if validator is None:
            try:
                schema = self.fetch(schema, no_validate=True)
            except Exception:
                logger.error(f"Can not find schema : {schema}")
            else:
                validator = _DefaultValidatingValidator(schema, resolver=self)
                self._validator[schema["$id"]] = validator

        if validator is not None:
            validator.validate(doc)

        return doc

    def _do_fetch(self, uri):
        uri = self.normalize_uri(uri)
        new_doc = self._cache.get(uri, None)
        if new_doc is not None:
            return new_doc

        for a_uri in self._alias.match(uri):
            new_doc = io.read(a_uri)

            if not new_doc:
                pass
            else:
                new_doc["$id"] = uri
                new_doc["$source_file"] = a_uri
                self._cache[uri] = new_doc
                break

        return new_doc

    def fetch(self, doc, no_validate=False) -> dict:
        """fetch document from source, then validate and fill default
        value basing on $schema in document
        """

        if isinstance(doc, (str, collections.abc.Sequence)):
            new_doc = self._do_fetch(doc)
        elif isinstance(doc, collections.abc.Mapping):
            new_doc = copy(doc)
        else:
            raise TypeError(type(doc))

        if isinstance(new_doc, collections.abc.Mapping):
            # new_doc["$schema"] = self.normalize_uri(new_doc.get("$schema", ""))
            if not no_validate and self._enable_validate:
                self.validate(new_doc)

        return new_doc

    def clear_cache(self):
        self._cache.clear()  # pylint: disable= no-member

    def glob(self, mod=None):
        mod_prefix = self.normalize_uri(f"{mod or ''}%_PATH_%")

        for n_uri in self._alias.match(mod_prefix):
            for p, f in io.glob(n_uri):
                yield p, f

    ##########################################################################
    # Begin: compatible with jsonschema.RefResolver

    @classmethod
    def from_schema(cls_, schema, base_uri=None):
        # if schema is None:
        #     return cls_()
        # s_id = schema.get("$id", "")
        # base_uri = base_uri or cls_._base_uri
        # res = cls_(base_uri=base_uri)
        # res.insert(s_id, schema)
        return cls_()

    def push_scope(self, scope):
        self._scopes_stack.append(uri_join(self.resolution_scope, scope))

    def pop_scope(self):
        try:
            self._scopes_stack.pop()
        except IndexError:
            raise IndexError("Failed to pop from an empty stack")

    @property
    def resolution_scope(self):
        return self._scopes_stack[-1]

    @contextlib.contextmanager
    def in_scope(self, scope):
        self.push_scope(scope)
        try:
            yield
        finally:
            self.pop_scope()

    @contextlib.contextmanager
    def resolving(self, ref):
        uri, resolved = self.resolve(ref)
        self.push_scope(uri)
        try:
            yield resolved
        finally:
            self.pop_scope()

    def resolve(self, ref):
        """Parse reference or description, return URI and full schema"""
        uri = self.normalize_uri(ref)
        return uri, self.fetch(uri, no_validate=True)

    def resolve_from_uri(self, uri):
        return self.fetch(uri, no_validate=True)

    def resolve_remote(self, uri):
        return self.fetch(uri, no_validate=True)

    def resolve_local(self, local_path):
        return self.fetch(uri_join("local://", local_path), no_validate=True)

    def resolve_fragment(self, obj, fragment):
        return getvalue_r(obj, fragment)

    # END :compatible with jsonschema.RefResolver
    ##########################################################################

    # RefResolver.HANDLERS["pyobject"] = lambda p: {
    #     "$schema": "PyObject", "$class": p}
