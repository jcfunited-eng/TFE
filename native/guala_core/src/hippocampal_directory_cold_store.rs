//! Durable content-addressed hippocampal cold custody in one local directory.
//!
//! Every retained object is immutable and named by the lowercase hex SHA-256
//! of its exact body, matching the canonical hippocampal addressing law
//! (`publish_hippocampal_admission` refuses any object whose address is not
//! the digest of its bytes).  Publication stages every object of the supplied
//! delta to a private temporary name, fsyncs it, and only then renames each
//! object into its content address.  Because addresses are content digests,
//! an interrupted publication can leave only content-verified objects that no
//! committed checkpoint references yet; the retrying publication re-verifies
//! byte equality and therefore observes the complete delta or none of it.
//! This store never mutates or deletes an object.

use crate::hippocampal_sparse_path::{HippocampalColdObject, HippocampalColdPort};
use crate::sha256::sha256;
use std::fs;
use std::io::{ErrorKind, Write};
use std::path::{Path, PathBuf};

fn hex_address(address: [u8; 32]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(64);
    for byte in address {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

fn sync_directory(path: &Path) -> Result<(), String> {
    let handle = fs::File::open(path)
        .map_err(|error| format!("hippocampal cold directory is unreadable: {error}"))?;
    handle
        .sync_all()
        .map_err(|error| format!("hippocampal cold directory sync failed: {error}"))
}

#[derive(Debug)]
pub(crate) struct DirectoryHippocampalColdStore {
    root: PathBuf,
}

impl DirectoryHippocampalColdStore {
    pub(crate) fn open(root: &Path) -> Result<Self, String> {
        fs::create_dir_all(root).map_err(|error| {
            format!(
                "hippocampal cold directory {} cannot be created: {error}",
                root.display()
            )
        })?;
        Ok(Self {
            root: root.to_path_buf(),
        })
    }

    fn object_path(&self, address: [u8; 32]) -> PathBuf {
        self.root.join(hex_address(address))
    }
}

impl HippocampalColdPort for DirectoryHippocampalColdStore {
    fn read_object(&self, address: [u8; 32]) -> Result<Option<Box<[u8]>>, String> {
        match fs::read(self.object_path(address)) {
            Ok(body) => {
                if sha256(&body) != address {
                    return Err(format!(
                        "hippocampal cold object {} does not match its content address",
                        hex_address(address)
                    ));
                }
                Ok(Some(body.into_boxed_slice()))
            }
            Err(error) if error.kind() == ErrorKind::NotFound => Ok(None),
            Err(error) => Err(format!(
                "hippocampal cold object {} is unreadable: {error}",
                hex_address(address)
            )),
        }
    }

    fn publish_atomic(&mut self, objects: &[HippocampalColdObject]) -> Result<(), String> {
        for object in objects {
            if sha256(object.body()) != object.address() {
                return Err(format!(
                    "hippocampal cold publication object {} is not content-addressed",
                    hex_address(object.address())
                ));
            }
        }
        let mut staged: Vec<(PathBuf, PathBuf)> = Vec::with_capacity(objects.len());
        let stage_result = (|| -> Result<(), String> {
            for object in objects {
                let target = self.object_path(object.address());
                match fs::read(&target) {
                    Ok(existing) => {
                        if existing.as_slice() != object.body() {
                            return Err(format!(
                                "hippocampal cold object {} exists with different bytes",
                                hex_address(object.address())
                            ));
                        }
                        continue;
                    }
                    Err(error) if error.kind() == ErrorKind::NotFound => {}
                    Err(error) => {
                        return Err(format!(
                            "hippocampal cold object {} is unreadable: {error}",
                            hex_address(object.address())
                        ));
                    }
                }
                let stage = self.root.join(format!(
                    ".stage-{}-{}",
                    hex_address(object.address()),
                    std::process::id(),
                ));
                let mut handle = fs::OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(&stage)
                    .map_err(|error| {
                        format!("hippocampal cold stage cannot be created: {error}")
                    })?;
                let write_result = handle
                    .write_all(object.body())
                    .and_then(|()| handle.sync_all())
                    .map_err(|error| format!("hippocampal cold stage write failed: {error}"));
                drop(handle);
                if let Err(error) = write_result {
                    let _ = fs::remove_file(&stage);
                    return Err(error);
                }
                staged.push((stage, target));
            }
            for (stage, target) in &staged {
                fs::rename(stage, target).map_err(|error| {
                    format!("hippocampal cold publication rename failed: {error}")
                })?;
            }
            Ok(())
        })();
        if let Err(error) = stage_result {
            for (stage, _target) in &staged {
                let _ = fs::remove_file(stage);
            }
            return Err(error);
        }
        sync_directory(&self.root)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn object(body: &[u8]) -> HippocampalColdObject {
        HippocampalColdObject::from_parts(sha256(body), body.to_vec().into_boxed_slice())
    }

    #[test]
    fn published_objects_cold_read_exactly_and_absence_is_none() {
        let root = std::env::temp_dir().join(format!(
            "guala-cold-store-test-{}-{}",
            std::process::id(),
            line!(),
        ));
        let _ = fs::remove_dir_all(&root);
        let mut store = DirectoryHippocampalColdStore::open(&root).unwrap();
        let first = object(b"first-cold-body");
        let second = object(b"second-cold-body");
        store
            .publish_atomic(std::slice::from_ref(&first))
            .unwrap();
        store
            .publish_atomic(&[first.clone(), second.clone()])
            .unwrap();
        assert_eq!(
            store.read_object(first.address()).unwrap().as_deref(),
            Some(first.body())
        );
        assert_eq!(
            store.read_object(second.address()).unwrap().as_deref(),
            Some(second.body())
        );
        assert_eq!(store.read_object(sha256(b"absent")).unwrap(), None);
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn misaddressed_publication_is_refused_before_any_write() {
        let root = std::env::temp_dir().join(format!(
            "guala-cold-store-test-{}-{}",
            std::process::id(),
            line!(),
        ));
        let _ = fs::remove_dir_all(&root);
        let mut store = DirectoryHippocampalColdStore::open(&root).unwrap();
        let wrong =
            HippocampalColdObject::from_parts(sha256(b"other"), b"body".to_vec().into_boxed_slice());
        assert!(store
            .publish_atomic(std::slice::from_ref(&wrong))
            .unwrap_err()
            .contains("not content-addressed"));
        assert_eq!(fs::read_dir(&root).unwrap().count(), 0);
        let _ = fs::remove_dir_all(&root);
    }
}
