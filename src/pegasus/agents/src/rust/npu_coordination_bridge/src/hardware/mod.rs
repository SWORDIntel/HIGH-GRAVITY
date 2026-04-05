//! Hardware abstraction layer for NPU coordination bridge

pub mod intel;

pub use intel::{IntelNPUManager, NPUCapabilities, NPUStatus};