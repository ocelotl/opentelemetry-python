# tests/_pyprotobuf/test_benchmark.py
#
# Benchmark: _pyprotobuf (pure-Python) vs google.protobuf (C extension)
# encoding speed on an equivalent generic proto3 message.
#
# The proto schema used here has no relation to OpenTelemetry — it is a
# standalone "Record" message with one field of every type that _pyprotobuf
# exposes a helper for: string, uint64, double, bool, bytes, fixed64, fixed32,
# an embedded sub-message, packed repeated uint64, and packed repeated double.
#
# The google.protobuf side uses the runtime descriptor / message-factory API
# to build the same schema dynamically, so no .proto file or protoc step is
# needed.
#
# Run:
#   uv run pytest tests/_pyprotobuf/test_benchmark.py -v --benchmark-sort=mean

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from opentelemetry.pyproto._pyprotobuf.fields import (
    bool_field,
    byt,
    dbl,
    fix32,
    fix64,
    msg,
    packed_double,
    packed_uint64,
    string,
    u64,
)

# ── Dynamic proto3 message definition ─────────────────────────────────────────
#
# Field map (mirrors the pyproto encoding function below):
#
#   field 1  – string    name
#   field 2  – uint64    count
#   field 3  – double    value
#   field 4  – bool      active
#   field 5  – bytes     data
#   field 6  – fixed64   timestamp_ns
#   field 7  – fixed32   flags
#   field 8  – Inner     inner            (embedded message)
#   field 9  – uint64[]  bucket_counts    (packed repeated)
#   field 10 – double[]  bounds           (packed repeated)
#
# Inner:
#   field 1  – string    label
#   field 2  – uint64    seq

_T = descriptor_pb2.FieldDescriptorProto


def _build_pb_classes():
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "pyproto_benchmark.proto"
    file_proto.syntax = "proto3"

    inner_proto = file_proto.message_type.add()
    inner_proto.name = "Inner"
    for name, number, type_id in (
        ("label", 1, _T.TYPE_STRING),
        ("seq",   2, _T.TYPE_UINT64),
    ):
        f = inner_proto.field.add()
        f.name = name; f.number = number; f.type = type_id; f.label = _T.LABEL_OPTIONAL

    rec_proto = file_proto.message_type.add()
    rec_proto.name = "Record"
    for name, number, type_id, label in (
        ("name",          1,  _T.TYPE_STRING,  _T.LABEL_OPTIONAL),
        ("count",         2,  _T.TYPE_UINT64,  _T.LABEL_OPTIONAL),
        ("value",         3,  _T.TYPE_DOUBLE,  _T.LABEL_OPTIONAL),
        ("active",        4,  _T.TYPE_BOOL,    _T.LABEL_OPTIONAL),
        ("data",          5,  _T.TYPE_BYTES,   _T.LABEL_OPTIONAL),
        ("timestamp_ns",  6,  _T.TYPE_FIXED64, _T.LABEL_OPTIONAL),
        ("flags",         7,  _T.TYPE_FIXED32, _T.LABEL_OPTIONAL),
        ("bucket_counts", 9,  _T.TYPE_UINT64,  _T.LABEL_REPEATED),
        ("bounds",        10, _T.TYPE_DOUBLE,  _T.LABEL_REPEATED),
    ):
        f = rec_proto.field.add()
        f.name = name; f.number = number; f.type = type_id; f.label = label

    inner_field = rec_proto.field.add()
    inner_field.name = "inner"
    inner_field.number = 8
    inner_field.type = _T.TYPE_MESSAGE
    inner_field.label = _T.LABEL_OPTIONAL
    inner_field.type_name = "Inner"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    Inner  = message_factory.GetMessageClass(pool.FindMessageTypeByName("Inner"))
    Record = message_factory.GetMessageClass(pool.FindMessageTypeByName("Record"))
    return Inner, Record


_Inner, _Record = _build_pb_classes()

# ── Benchmark data ─────────────────────────────────────────────────────────────

_NAME          = "benchmark.record.example"
_COUNT         = 9_876_543_210
_VALUE         = 3.141592653589793
_ACTIVE        = True
_DATA          = b"\xde\xad\xbe\xef" * 8
_TS            = 1_782_401_900_556_236_527
_FLAGS         = 0xDEAD
_INNER_LABEL   = "inner.label"
_INNER_SEQ     = 42
_BUCKET_COUNTS = [0, 1, 4, 12, 35, 78, 120, 89, 42, 15, 4, 1, 0]
_BOUNDS        = [0.0, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

# ── pyproto encoder ────────────────────────────────────────────────────────────

def _pyproto_encode() -> bytes:
    inner = string(1, _INNER_LABEL) + u64(2, _INNER_SEQ)
    return (
        string(1, _NAME)
        + u64(2, _COUNT)
        + dbl(3, _VALUE)
        + bool_field(4, _ACTIVE)
        + byt(5, _DATA)
        + fix64(6, _TS)
        + fix32(7, _FLAGS)
        + msg(8, inner)
        + packed_uint64(9, _BUCKET_COUNTS)
        + packed_double(10, _BOUNDS)
    )


# ── google.protobuf encoder ────────────────────────────────────────────────────

def _pb_encode() -> bytes:
    return _Record(
        name=_NAME,
        count=_COUNT,
        value=_VALUE,
        active=_ACTIVE,
        data=_DATA,
        timestamp_ns=_TS,
        flags=_FLAGS,
        inner=_Inner(label=_INNER_LABEL, seq=_INNER_SEQ),
        bucket_counts=_BUCKET_COUNTS,
        bounds=_BOUNDS,
    ).SerializeToString()


# ── Correctness ────────────────────────────────────────────────────────────────

def test_encode_outputs_identical() -> None:
    assert _pyproto_encode() == _pb_encode()


# ── Benchmarks ─────────────────────────────────────────────────────────────────

def test_encode_pyproto(benchmark) -> None:
    result = benchmark(_pyproto_encode)
    assert len(result) > 0


def test_encode_protobuf(benchmark) -> None:
    result = benchmark(_pb_encode)
    assert len(result) > 0
