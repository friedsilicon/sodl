
fn main() {
    for arg in std::env::args().skip(1) {
        let src = std::fs::read_to_string(&arg).unwrap();
        match sodl::parser::parse(&src) {
            Ok(d) => print!("{}", sodl::tree::render(&d)),
            Err(e) => { eprintln!("{}: {}", arg, e.join("; ")); std::process::exit(1); }
        }
    }
}
