# developing bed (portfolio management cli tool)

## beginning

- the project is inspired on - [bud](https://github.com/cardosoccc/bud)
- it should have commands following the same design principles
- read the repository, us the same project structure
- use cli commands in the same way, same argument principles (one word aliases)

## similarities

- a project on bud it's similar to the portfolio on bed
- portfolio create should be similar to `bud db init`
- portfolio delete should be similar to `bud db destroy`
- portfolio push should be similar to `bud db push`
- portfolio pull should be similar to `bud db pull`
- pull and push should support aws and gcp, just as bud does

## strategy

- for every feature being iomplemented, a complete set of test scenarios should be planned and proposed;
- after confirmation, tests should be implemented first, and features should make tests pass;
