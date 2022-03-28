function registerCardListeners() {
  $(".usercard").dblclick(function() {
      $(this).toggleClass("flip")
      $(this).find('.front').toggleClass('d-none')
      $(this).find('.back').toggleClass('d-none')
    })
}
function shuffle(x) {
  return x.sort(() => Math.random() - 0.5)
}
// Mount cards
Vue.createApp({
  data() {
    return {
      token: window.localStorage.getItem('flashcard-token'),
      current_user: {},
      deck: {},
      exercise_on: false,
      seen_cards: [],
      correct: 0,
      cards: [],
      exportLink: ""
    }
  },
  mounted() {
    fetch("/user?auth_token=" + this.token).then((resp) => {
      if (resp.ok) {
        return resp.json()
      }
    }).then((data) => {
      this.current_user = data
    })
    let deck_id = new URL(window.location.href).pathname.split('/').slice(-1).pop()
    fetch('/deck?id=' + deck_id + '&auth_token=' + this.token).then((resp) => {
      if (resp.ok) {
        return resp.json()
      }
    }).then((data) => {
      this.deck = data
      this.exportLink = `/export/${this.deck.id}?auth_token=${this.token}`
      this.deck.cards.forEach((card) => {
        card.orgid = card.id
        card.id = ""
        card.id = "usercard-" + card.orgid
        card.src = `/upload/${card.image}?auth_token=${this.token}`
        card.imgid = "card-" + card.orgid
      })
    })
  },
  methods: {
    passThroughCards() {
      $('.cardpreview').empty()
      $('#cardprompt').val('')

      if (this.cards.length == 0) {
        let score = this.correct / this.seen_cards.length * 100
        alert(`Done! You scored ${score}%`)
        $.ajax({
          url: `/scores/${this.deck.id}?auth_token=` + this.token,
          method: 'POST',
          data: JSON.stringify({score: score, deck: this.deck.id}),
          contentType: 'application/json',
          processData: false,
          success: function(resp) {
            window.location.reload()
          }
        })
      }
      let card = this.cards.pop()
      this.seen_cards.push(card)
      $('.cardpreview').append($(card).clone())
      return true
    },
    startExercise() {
      this.exercise_on = !(this.exercise_on)
      let text = this.exercise_on ? "Done? Stop the Exercise." : "Ready? Start the Exercise!"
      $('#start-exercise').text(text)
      $('#start-exercise').toggleClass("btn-warning")
      $('.cardrow').toggleClass('d-none')
      if (this.exercise_on) {
        this.cards = shuffle($('.usercard').toArray())
        $('#cardprompt').attr('disabled', false)
        this.seen_cards = []
        this.correct = 0
        $('.cardpreview').removeClass('d-none')
        $('#cardanswer').removeClass('d-none')
        this.passThroughCards()
      } else {
        $('.cardpreview').empty()
        $('#cardanswer').addClass('d-none')
      }
    },
    submitAnswer(e) {
      e.preventDefault()
      let actual = $('#cardprompt').val()
      let ideal = $('.cardpreview').find('.card').find('.back').find('.card-body').find('.card-text').text()
      if (ideal.toLowerCase() == actual.toLowerCase()) {
        this.correct = this.correct + 1
        $('.rightwrong').text('Correct!')
        $('.rightwrong').addClass('text-success')
        $('.rightwrong').removeClass('text-danger')
      } else {
        $('.rightwrong').text('Incorrect 😓')
        $('.rightwrong').addClass('text-danger')
        $('.rightwrong').removeClass('text-success')
      }
      $('.correctanswer').text(ideal)
      $('.toast').show()
      setTimeout(function() {
        $('.toast').hide()
        this.passThroughCards()
      }.bind(this), 1000)
    }
  },
  updated() {
    registerCardListeners()
  }
}).mount('#app')
