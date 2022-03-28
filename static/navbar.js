navApp = Vue.createApp({
  data() {
    return {
      token: window.localStorage.getItem('flashcard-token'),
      current_user: {},
      homelink: "/?auth_token=" + window.localStorage.getItem('flashcard-token')
    }
  },
  mounted() {
    fetch("http://localhost:5000/user?auth_token=" + this.token).then((resp) => {
      if (resp.ok) {
        return resp.json()
      }
    }).then((data) => {
      this.current_user = data
    })
  }
}).mount('.navbar')
