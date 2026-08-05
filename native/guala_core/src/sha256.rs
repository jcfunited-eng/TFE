//! Allocation-free streaming SHA-256 for immutable native record custody.
//!
//! `sha2::Sha256` retains only its fixed digest state and one fixed-size block.
//! It consumes the caller's bytes directly, so hashing does not allocate or
//! construct an input-sized padded copy.

use sha2::{Digest, Sha256};

pub fn sha256(input: &[u8]) -> [u8; 32] {
    Sha256::digest(input).into()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hex(value: &[u8]) -> String {
        use std::fmt::Write;

        let mut output = String::with_capacity(value.len() * 2);
        for byte in value {
            write!(&mut output, "{byte:02x}").expect("String writes cannot fail");
        }
        output
    }

    #[test]
    fn matches_fips_180_4_vectors() {
        assert_eq!(
            hex(&sha256(b"")),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        );
        assert_eq!(
            hex(&sha256(b"abc")),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        );
        assert_eq!(
            hex(&sha256(
                b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
            )),
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
        );
    }

    #[test]
    fn matches_padding_boundary_vectors() {
        for (length, expected) in [
            (
                55,
                "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318",
            ),
            (
                56,
                "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a",
            ),
            (
                63,
                "7d3e74a05d7db15bce4ad9ec0658ea98e3f06eeecf16b4c6fff2da457ddc2f34",
            ),
            (
                64,
                "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb",
            ),
            (
                65,
                "635361c48bb9eab14198e76ea8ab7f1a41685d6ad62aa9146d301d4f17eb0ae0",
            ),
        ] {
            let input = vec![b'a'; length];
            assert_eq!(hex(&sha256(&input)), expected, "length {length}");
        }
    }

    #[test]
    fn matches_multi_megabyte_vector() {
        let input = vec![0_u8; 5 * 1024 * 1024 + 17];
        assert_eq!(
            hex(&sha256(&input)),
            "0c086025b0bbb57526aa3a8444e22ec65d0ce52e497cfba54e5ac826ee9d1444",
        );
    }

    #[test]
    fn production_digest_path_has_no_dynamic_buffer_constructor() {
        let source = include_str!("sha256.rs");
        let dynamic_buffer_constructor = ["V", "ec", "::"].concat();
        let capacity_constructor = ["with_", "capacity"].concat();

        let production = source
            .split("#[cfg(test)]")
            .next()
            .expect("production SHA-256 source exists");
        assert!(!production.contains(&dynamic_buffer_constructor));
        assert!(!production.contains(&capacity_constructor));
        assert!(production.contains("Sha256::digest(input)"));
    }
}
