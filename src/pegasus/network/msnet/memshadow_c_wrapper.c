/**
 * Python C Extension Wrapper for MEMSHADOW Protocol
 *
 * Provides Python bindings for the C binary implementation.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdbool.h>
#include "../c/memshadow.h"

static PyObject *memshadow_pack_header_py(PyObject *self, PyObject *args) {
    memshadow_header_t header;
    uint8_t buffer[MEMSHADOW_HEADER_SIZE];

    if (!PyArg_ParseTuple(args, "KHHHHIIQ",
            &header.magic,
            &header.version,
            &header.priority,
            &header.msg_type,
            &header.flags_batch,
            &header.payload_len,
            &header.timestamp_ns,
            &header.sequence_num)) {
        return NULL;
    }

    int ret = memshadow_pack_header(&header, buffer, sizeof(buffer));
    if (ret < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to pack header");
        return NULL;
    }

    return PyBytes_FromStringAndSize((char *)buffer, MEMSHADOW_HEADER_SIZE);
}

static PyObject *memshadow_unpack_header_py(PyObject *self, PyObject *args) {
    Py_buffer buffer;
    memshadow_header_t header;

    if (!PyArg_ParseTuple(args, "y*", &buffer)) {
        return NULL;
    }

    if (buffer.len < MEMSHADOW_HEADER_SIZE) {
        PyBuffer_Release(&buffer);
        PyErr_SetString(PyExc_ValueError, "Buffer too short");
        return NULL;
    }

    int ret = memshadow_unpack_header((uint8_t *)buffer.buf, buffer.len, &header);
    PyBuffer_Release(&buffer);

    if (ret < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to unpack header");
        return NULL;
    }

    return Py_BuildValue("(KHHHHIIQ)",
            header.magic,
            header.version,
            header.priority,
            header.msg_type,
            header.flags_batch,
            header.payload_len,
            header.timestamp_ns,
            header.sequence_num);
}

static PyObject *memshadow_validate_header_py(PyObject *self, PyObject *args) {
    memshadow_header_t header;

    if (!PyArg_ParseTuple(args, "KHHHHIIQ",
            &header.magic,
            &header.version,
            &header.priority,
            &header.msg_type,
            &header.flags_batch,
            &header.payload_len,
            &header.timestamp_ns,
            &header.sequence_num)) {
        return NULL;
    }

    bool result = memshadow_validate_header(&header);
    return PyBool_FromLong(result);
}

static PyObject *memshadow_get_timestamp_ns_py(PyObject *self, PyObject *args) {
    uint64_t timestamp = memshadow_get_timestamp_ns();
    return PyLong_FromUnsignedLongLong(timestamp);
}

static PyObject *memshadow_compute_hmac_py(PyObject *self, PyObject *args) {
    Py_buffer data_buf, key_buf;
    uint8_t hmac_output[48]; // SHA384 is 48 bytes

    if (!PyArg_ParseTuple(args, "y*y*", &data_buf, &key_buf)) {
        return NULL;
    }

    int ret = memshadow_compute_hmac(
        (const uint8_t *)data_buf.buf, data_buf.len,
        (const uint8_t *)key_buf.buf, key_buf.len,
        hmac_output, sizeof(hmac_output)
    );

    PyBuffer_Release(&data_buf);
    PyBuffer_Release(&key_buf);

    if (ret < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to compute HMAC");
        return NULL;
    }

    return PyBytes_FromStringAndSize((char *)hmac_output, 32);
}

static PyObject *memshadow_pack_message_py(PyObject *self, PyObject *args) {
    memshadow_header_t header;
    Py_buffer payload_buf, key_buf;
    uint8_t *buffer = NULL;
    size_t buffer_size = 0;
    size_t message_size = 0;
    PyObject *key_obj = NULL;

    if (!PyArg_ParseTuple(args, "KHHHHIIQO y*",
            &header.magic,
            &header.version,
            &header.priority,
            &header.msg_type,
            &header.flags_batch,
            &header.payload_len,
            &header.timestamp_ns,
            &header.sequence_num,
            &key_obj,
            &payload_buf)) {
        return NULL;
    }

    // Calculate buffer size (header + payload + optional HMAC)
    buffer_size = MEMSHADOW_HEADER_SIZE + payload_buf.len;
    if (key_obj != Py_None) {
        buffer_size += 32; // HMAC size
    }

    buffer = (uint8_t *)malloc(buffer_size);
    if (!buffer) {
        PyBuffer_Release(&payload_buf);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate buffer");
        return NULL;
    }

    const uint8_t *integrity_key = NULL;
    size_t integrity_key_size = 0;

    if (key_obj != Py_None) {
        if (PyArg_ParseTuple(args, "KHHHHIIQO y* y*", NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, &key_buf)) {
            integrity_key = (const uint8_t *)key_buf.buf;
            integrity_key_size = key_buf.len;
        }
    }

    int ret = memshadow_pack_message(
        &header,
        (const uint8_t *)payload_buf.buf, payload_buf.len,
        buffer, buffer_size, &message_size,
        integrity_key, integrity_key_size
    );

    if (key_obj != Py_None) {
        PyBuffer_Release(&key_buf);
    }
    PyBuffer_Release(&payload_buf);

    if (ret < 0) {
        free(buffer);
        PyErr_SetString(PyExc_RuntimeError, "Failed to pack message");
        return NULL;
    }

    PyObject *result = PyBytes_FromStringAndSize((char *)buffer, message_size);
    free(buffer);
    return result;
}

static PyObject *memshadow_unpack_message_py(PyObject *self, PyObject *args) {
    Py_buffer buffer_buf, key_buf;
    memshadow_header_t header;
    uint8_t *payload_buffer = NULL;
    size_t payload_size = 0;
    size_t max_payload_size = 16 * 1024 * 1024; // 16MB
    PyObject *key_obj = NULL;

    if (!PyArg_ParseTuple(args, "y* O", &buffer_buf, &key_obj)) {
        return NULL;
    }

    payload_buffer = (uint8_t *)malloc(max_payload_size);
    if (!payload_buffer) {
        PyBuffer_Release(&buffer_buf);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate payload buffer");
        return NULL;
    }

    const uint8_t *integrity_key = NULL;
    size_t integrity_key_size = 0;

    if (key_obj != Py_None) {
        if (PyArg_ParseTuple(args, "y* O y*", NULL, NULL, &key_buf)) {
            integrity_key = (const uint8_t *)key_buf.buf;
            integrity_key_size = key_buf.len;
        }
    }

    int ret = memshadow_unpack_message(
        (const uint8_t *)buffer_buf.buf, buffer_buf.len,
        &header,
        payload_buffer, max_payload_size, &payload_size,
        integrity_key, integrity_key_size
    );

    if (key_obj != Py_None) {
        PyBuffer_Release(&key_buf);
    }
    PyBuffer_Release(&buffer_buf);

    if (ret < 0) {
        free(payload_buffer);
        PyErr_SetString(PyExc_RuntimeError, "Failed to unpack message");
        return NULL;
    }

    PyObject *header_tuple = Py_BuildValue("(KHHHHIIQ)",
            header.magic,
            header.version,
            header.priority,
            header.msg_type,
            header.flags_batch,
            header.payload_len,
            header.timestamp_ns,
            header.sequence_num);

    PyObject *payload_bytes = PyBytes_FromStringAndSize((char *)payload_buffer, payload_size);
    free(payload_buffer);

    PyObject *result = PyTuple_New(2);
    PyTuple_SetItem(result, 0, header_tuple);
    PyTuple_SetItem(result, 1, payload_bytes);

    return result;
}

static PyMethodDef MemshadowMethods[] = {
    {"pack_header", memshadow_pack_header_py, METH_VARARGS, "Pack MEMSHADOW header"},
    {"unpack_header", memshadow_unpack_header_py, METH_VARARGS, "Unpack MEMSHADOW header"},
    {"validate_header", memshadow_validate_header_py, METH_VARARGS, "Validate MEMSHADOW header"},
    {"get_timestamp_ns", memshadow_get_timestamp_ns_py, METH_NOARGS, "Get current timestamp in nanoseconds"},
    {"compute_hmac", memshadow_compute_hmac_py, METH_VARARGS, "Compute HMAC-SHA384"},
    {"pack_message", memshadow_pack_message_py, METH_VARARGS, "Pack complete MEMSHADOW message"},
    {"unpack_message", memshadow_unpack_message_py, METH_VARARGS, "Unpack complete MEMSHADOW message"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef memshadow_c_module = {
    PyModuleDef_HEAD_INIT,
    "memshadow._memshadow_c",
    "MEMSHADOW Protocol C Extension",
    -1,
    MemshadowMethods
};

PyMODINIT_FUNC PyInit__memshadow_c(void) {
    return PyModule_Create(&memshadow_c_module);
}
