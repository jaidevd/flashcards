Vue.createApp({
  data() {
    return {
      front: 'Text on the front of the card.',
      back: 'Text on the back of the card.',
      image: ''
    }
  },
  methods: {
    flipCard() {
      $('.card').toggleClass("flip")
      $('.front').toggleClass('d-none')
      $('.back').toggleClass('d-none')
    },
    addCard(e) {
      let token = window.localStorage.getItem('flashcard-token')
      $.ajax({
        url: '/card/?auth_token=' + token,
        method: 'POST',
        data: JSON.stringify($('form').serializeArray()),
        processData: false,
        contentType: 'application/json',
        success: function(resp) {
          window.location.reload()
        }
      })
    }
  }
}).mount('#app')
