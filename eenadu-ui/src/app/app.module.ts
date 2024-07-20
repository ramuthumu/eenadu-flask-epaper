import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { HttpClientModule } from '@angular/common/http'; // Add this line
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { EditionsComponent } from './editions/editions.component';

@NgModule({
  declarations: [
    AppComponent,
    EditionsComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule, // And this line
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
