npm install dotenv
require("dotenv").config();
console.log(importantVariable);
const mySecret = process.env.TEST
console.log(`The value of MY_SECRET is: ${mySecret}`);
