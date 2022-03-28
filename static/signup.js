Vue.createApp({
  data() {
    return {
      token: window.localStorage.getItem('flashcard-token'),
      current_user: {},
      homelink: "/?auth_token=" + window.localStorage.getItem('flashcard-token'),
      existing_user: {
        exists: false,
        email: ''
      }
    }
  },
  mounted() {
    window.localStorage.removeItem('flashcard-token')
  },
  methods: {
    signup(e) {
      e.preventDefault()
      $.ajax({
        url: '/signup',
        method: 'POST',
        data: JSON.stringify({
          email: $('#email').val(),
          password: $('#password-1').val()
        }),
        processData: false,
        contentType: 'putapplication/json',
        error: function(xhr, textStatus, error) {
          if (xhr.status == 400) {
            this.existing_user.email = $('#email').val()
            this.existing_user.exists = true
          }
        }.bind(this),
        success: function(data) {
          window.location.href = "/login"
        }
      })
    }
  }
}).mount('.container')
