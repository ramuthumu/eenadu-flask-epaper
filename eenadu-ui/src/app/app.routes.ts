import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { EditionsComponent } from './editions/editions.component';

export const routes: Routes = [
  { path: '', component: EditionsComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
