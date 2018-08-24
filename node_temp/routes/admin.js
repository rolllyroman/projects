var express = require('express')

var admin = express.Router()

admin.get('/admin/login', function (req, res) {
  res.end("admin/login!!!!")
})

module.exports = admin
