# bed - portfolio management cli

- portfolio management cli tool
- built to be used by ai agents
- help users manage their personal financial assets
- follow the same design principles of bud (budget management cli)
- "bed" comes from keeping tou money under the bed

## domain model

- portfolios
  - a portfolio represents the top level project
  - it should not be a separate table
  - the database itself represents the portfolio

- goal
  - the goal of the investment, like "retirement", "emergency funds", etc.
  - can be a quantity goal, an invested value goal, or a current value goal
  - attributes
    - description
    - class
    - quantity
    - value

- asset (an specific asset in the portfolio)
  - name
  - description
  - class (equity / fixed-income)
  - type (stock / bond)
  - quantity
  - initial_value
  - current_value
  - goal_id
  - category
  - subcategory
  - tags

- rules
  - represents a limit, or a desired proportion of some asset, or class, or type, or category, or subcategory, or tags
  - limits can be specific to a complete set of attributes, one just one
  - attributes
    - invested_value
    - current_value
    - description (should match the asset description if the rule is specific to an asset)
    - class
    - type
    - tags
    - category
    - subcategory

## features

- create a portfolio (bed portfolio init)
- delete a portfolio (bed portfolio destroy)
- push a portfolio (bed portfolio push)
- pull a portfolio (bed portfolio pull)
- show portfolio status (to be implemented later)

- list assets
- create an asset
- update an asset
- delete an asset

- list goals
- create an goal
- update an goal
- delete an goal

- list rules
- create an rule
- update an rule
- delete an rule

## non-funcional requirements

- should use a local sqlite database
- should be written in python
- should use the click framework
- should use the sqlalchemy framework
- should follow the same principles of bud
- should use uv

## references

- [bud](https://github.com/cardosoccc/bud)
