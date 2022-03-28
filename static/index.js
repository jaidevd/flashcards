// Mount decklist
Vue.createApp({
  data() {
    return {
      token: window.localStorage.getItem('flashcard-token'),
      current_user: {},
      decklink: `/deck/create?auth_token=` + window.localStorage.getItem('flashcard-token'),
      cardlink: `/card/create?auth_token=` + window.localStorage.getItem('flashcard-token'),
    }
  },
  mounted() {
    fetch("/user?auth_token=" + this.token).then((resp) => {
      if (resp.ok) {
        return resp.json()
      }
    }).then((data) => {
      this.current_user = data
      this.current_user.decks.forEach((deck) => {
        deck.deck_url = `/deck/${deck.id}?auth_token=` + this.token
        deck.del_id = `deldeck-${deck.id}`
      })
    })
  },
  methods: {
    sendReport() {
      fetch('/report?auth_token=' + token)
      .then((r) => {
        if (r.ok) {
          alert('Your report is being generated. Please check your inbox.')
        }
      })
    }
  }
}).mount('.container')
