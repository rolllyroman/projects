var admin = express.Router()

router.get('/', function (req, res) {
  res.end("admin/admin!!!!")
})

module.exports = admin
